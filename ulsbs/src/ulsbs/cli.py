# SPDX-FileCopyrightText: 2016-2026 Lari Natri <lari.natri@iki.fi>
# SPDX-License-Identifier: GPL-3.0-or-later

"""
Command Line Interface.
This file is part of the 'ulsbs' package.
"""

from __future__ import annotations

import argparse
import os
import uuid
from pathlib import Path
from typing import List

import ulsbs.resultlist as resultlist

from .config import build_config, Config
from .deploy import deploy_results
from .docker import run_self_in_docker
from .engine_assets import EngineAssets
from .jobs import build_job_queue
from .paths import ProjectPaths
from .pipeline import require_tools, run_jobs_parallel
from .tempdir import setup_temp_dir, clear_temp_dir_if_no_locks
from .ui import UI
from .util import ensure_dir, run_cmd, which, create_unique_id

class ArgFormatter(argparse.ArgumentDefaultsHelpFormatter, argparse.RawDescriptionHelpFormatter):
    pass

def build_arg_parser(ui: UI) -> argparse.ArgumentParser:
    """Build and return the CLI argument parser."""
    p = argparse.ArgumentParser(
        prog="ulsbs-compile",
        description="Compile songbooks from sources using Unilaiva Songbook System (ULSBS)",
        epilog=(
            f"{ui.colorize('examples:', ui.C_LBLUE)}\n"
            "  ./ulsbs-compile *.tex\n"
            "  ./ulsbs-compile --no-deploy --no-extrainstr mybook.tex\n"
            "  ./ulsbs-compile --profile myprofile --no-audio --no-midi\n"
        ),
        formatter_class=ArgFormatter,
    )

    p.add_argument("files", nargs="*", help="Main songbook files to compile; takes precedence over songbooks defined in ulsbs-config.toml")

    p.add_argument("-q", action="store_true", help="Quick dev build: default variant only, no extras, no deploy")
    p.add_argument("--profile", default="default", help="Choose profile defined in ulsbs-config.toml to use")

    p.add_argument("--docker-rebuild", action="store_true", help="Force rebuilding of Docker image")
    p.add_argument("--no-docker", action="store_true", help="Compile on host instead of Docker (not recommended)")
    p.add_argument("--pull", action="store_true", help="Run 'git pull --rebase' before compiling")
    p.add_argument("--sequential", action="store_true", help="Do not compile in parallel (to conserve memory)")
    p.add_argument("--keep-temp", action="store_true", help="Do not clean temp directory even after successful compilation")
    p.add_argument("--max-log-lines", type=int, metavar="N", default=20, help="Maximum error log lines to display (0..1000)")

    prestr = p.add_argument_group("restricting options")
    prestr.add_argument("--no-deploy", action="store_true", help="Do not copy result files into deploy directory")
    prestr.add_argument("--no-printouts", action="store_true", help="Do not produce extra printouts for home printing")
    prestr.add_argument("--no-coverimage", action="store_true", help="Do not produce cover images as .png")
    prestr.add_argument("--no-midi", action="store_true", help="Do not produce MIDI files")
    prestr.add_argument("--no-audio", action="store_true", help="Do not produce MP3 audio files")
    prestr.add_argument("--no-lyric", action="store_true", help="Do not produce lyrics-only variant")
    prestr.add_argument("--no-extrainstr", action="store_true", help="Do not produce variants for extra instruments")

    pmodes = p.add_argument_group("special modes")
    pmodes.add_argument("--shell", action="store_true", help="Only open an interactive shell in the Docker container; perform no other actions")
    pmodes.add_argument("--deploy-last", action="store_true", help="Only deploy last compilation results; perform no other actions")
    pmodes.add_argument("--deploy-common", action="store_true", help="Only deploy common assets (icons, metadata); perform no other actions")

    return p


def print_plan_summary(
    ui: UI,
    cfg: Config,
    jobs_count: int,
) -> None:
    """Print a short summary of the planned compilation run."""

    def _yn(v: bool) -> str:
        return ui.colorize("YES" if v else "NO", ui.C_LBLUE)

    songbooks_count = len(cfg.songbooks)

    ui.info("")
    ui.info(ui.colorize(f"{'Compiling a songbook:' if songbooks_count == 1 else 'Compiling songbooks:'}", ui.C_WHITE))
    ui.info("")
    ui.info(f"  - Base profile: {ui.colorize(cfg.profile, ui.C_LBLUE)}")
    ui.info(f"  - Songbooks to compile: {ui.colorize(f'{songbooks_count}', ui.C_LBLUE)} {ui.colorize(f'({jobs_count} variant jobs)', ui.C_BLUE)}")
    ui.info(f"  - Using Docker: {_yn(cfg.use_docker or cfg.runtime.in_docker)}" + ("" if (cfg.use_docker or cfg.runtime.in_docker) else f" {ui.C_YELLOW}(this is not recommended!){ui.C_RESET}"))
    ui.info(f"  - Parallel compilation: {_yn(cfg.max_parallel > 1)}" + ui.colorize(f" ({cfg.max_parallel} workers)" if cfg.max_parallel > 1 else "", ui.C_BLUE))
    ui.info(f"  - Using system's /tmp for temp: {_yn(cfg.use_system_tmp)}")
    ui.info(f"  - Clean up temp after successful compilation: {_yn(cfg.clean_temp)}")
    ui.info(f"  - Additional lyrics only variants: {_yn(cfg.lyricbooks)}")
    ui.info(f"  - Additional extra instrument variants: {_yn(cfg.extrainstrumentbooks)}")
    ui.info(f"  - Create printouts: {_yn(cfg.create_printouts)}")
    ui.info(f"  - Extract covers as images: {_yn(cfg.coverimage)}")
    ui.info(f"  - Create MIDI files: {_yn(cfg.midifiles)}")
    ui.info(f"  - Create audio files: {_yn(cfg.audiofiles)}")
    ui.info(f"  - Deploy: {_yn(cfg.deploy)}")
    ui.info("")


def main(argv: List[str] | None = None) -> int:
    """CLI entrypoint. Returns process exit code."""

    def post_compile():
        """
        Does post-compile actions that need to be done on the host:
          - deploy
        """
        if cfg.runtime.in_docker:
            return
        # Use resultlist in result location
        resultlist.initialize(proj.result_dir, unique_id)
        if cfg.deploy and not cfg.shell:
            ui.info("")
            deploy_results(ui=ui, cfg=cfg)
        ui.info("")

    ui = UI(use_colors=True)
    assets = EngineAssets()
    ns = build_arg_parser(ui=ui).parse_args(argv)

    explicit_docs = [Path(x) for x in ns.files]
    proj = ProjectPaths.from_docs(explicit_docs)
    in_docker = bool(os.environ.get("ULSBS_INTERNAL_RUNNING_IN_CONTAINER"))
    unique_id = os.environ.get("ULSBS_INTERNAL_UNIQUE_ID", create_unique_id()) or create_unique_id()

    try:
        cfg = build_config(
            profile=getattr(ns, "profile", "default"),
            args_ns=ns,
            config_path=proj.config_file,
            env=os.environ,
            runtime_project_paths=proj,
            runtime_in_docker=in_docker,
            runtime_unique_id=unique_id,
        )
    except Exception as e:
        ui.info("")
        ui.error_line(f"Configuration error!")
        ui.space_line(f"Config file: {proj.config_file}")
        ui.space_line(ui.colorize(e, ui.C_YELLOW))
        ui.info("")
        return 1

    # Deploy-only modes use CWD as project root and are run outside container
    if cfg.deploy_last or cfg.deploy_common:
        mode_text = "Common files only" if cfg.deploy_common else "Latest results"
        ui.info("")
        ui.info(ui.colorize(f"Deploying existing files:", ui.C_WHITE))
        ui.info("")
        ui.info(f"  - Project root: {ui.colorize(cfg.runtime.project_paths.project_root, ui.C_LBLUE)}")
        ui.info(f"  - Mode: {ui.colorize(mode_text, ui.C_LBLUE)}")
        ui.info("")
        ensure_dir(cfg.runtime.project_paths.result_dir)
        if cfg.deploy_common:
            resultlist.initialize(cfg.runtime.project_paths.result_dir)
            resultlist.write_header()
            deploy_results(ui=ui, cfg=cfg)
        else: # deploy_last
            resultlist_files = resultlist.resultfiles_in_dir(proj.result_dir)
            if len(resultlist_files) > 0:
                for reslist in resultlist_files:
                    resultlist.initialize_with_file(reslist)
                    deploy_results(ui=ui, cfg=cfg)
            else:
                ui.nodeploy_line("Nothing to deploy!")
        ui.info("")
        return 0

    # Host-only git pull
    if cfg.pull and not cfg.in_docker:
        if which("git") is None:
            raise SystemExit("'git' binary not found in PATH, but pull requested!")
        ui.git_line("Pulling remote changes (with rebase)...")
        run_cmd(["git", "pull", "--rebase"], cwd=cfg.runtime.project_paths.project_root, check=True)

    # Host-only temp dir setup
    if not cfg.runtime.in_docker:
        setup_temp_dir(ui, cfg)

    # Docker (default) unless --no-docker
    if cfg.use_docker and not cfg.runtime.in_docker:
        passthrough = (argv if argv is not None else os.sys.argv[1:])

        rc = run_self_in_docker(
            ui=ui,
            assets=assets,
            cfg=cfg,
            passthrough_args=list(passthrough),
            script_file=Path(__file__),
        )

        # Host-side post-actions (deploy) after container finishes
        if rc == 0:
            post_compile()

        return rc

    # Shell-only mode
    if cfg.shell:
        ui.exec_line("Start interactive shell")
        os.execvp("bash", ["bash"])
        return 127

    require_tools()

    ensure_dir(cfg.runtime.project_paths.temp_dir)
    ensure_dir(cfg.runtime.project_paths.result_dir)

    # initialize resultfile in temp
    resultlist.initialize(cfg.runtime.project_paths.temp_dir, cfg.runtime.unique_id)
    resultlist.write_header()

    jobs = build_job_queue(cfg=cfg, doc_colors=ui.doc_colors)

    print_plan_summary(ui=ui, cfg=cfg, jobs_count=len(jobs))

    try:
        result = run_jobs_parallel(
            ui=ui,
            jobs=jobs,
            assets=assets,
            cfg=cfg,
        )
    except KeyboardInterrupt:
        # Mark result list and copy the resultlist into result/ so host-side
        # deploy tooling can see it, and exit quietly
        try:
            resultlist.abort(proj.result_dir)
        except Exception:
            pass

        ui.info("")
        ui.abort_line(ui.colorize("All unfinished jobs aborted by user intervention.", ui.C_YELLOW))
        ui.info("")

        return 130

    resultlist.finalize(dst_dir=proj.result_dir, runresult=result, delete_existing_resultlists_in_dst=True)

    if cfg.clean_temp and not result.failures:
        try:
            if clear_temp_dir_if_no_locks(proj.temp_dir):
                ui.debug_line("Temp cleared")
            else:
                ui.debug_line("Temp not cleared due to other jobs still running")
        except Exception as e:
            ui.warning_line(f"Temp not cleared due to an error: {str(e)}")
    else:
        ui.debug_line("Temp is kept.")

    if result.successes:
        ui.info("")
        ui.success_line(f"{'All' if len(result.successes) == len(jobs) else len(result.successes)} jobs succeeded.")
        if result.total_warnings:
            ui.warning_line(f"There were a total of {result.total_warnings} warnings in all jobs.")
            if cfg.clean_temp:
                ui.space_line("To keep the logs for analyzing warnings, run with --keep-temp")

    if result.failures:
        ui.info("")
        ui.fail_line(f"{'All' if len(result.failures) == len(jobs) else 'Some'} jobs failed:")
        for f in result.failures:
            ui.fail_line(f"  - {f.job.doc_stem}:{f.job.variant} -> {f.reason}")
        if cfg.deploy:
            ui.info("")
            ui.nodeploy_line("Nothing is deployed due to failures.")
        ui.info("")
        return 1

    if not cfg.runtime.in_docker:
         post_compile()

    return 0
