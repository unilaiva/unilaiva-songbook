# SPDX-FileCopyrightText: 2016-2026 Lari Natri <lari.natri@iki.fi>
# SPDX-License-Identifier: GPL-3.0-or-later

"""
Command Line Interface.
This file is part of the 'ulsbs' package.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import List

import ulsbs.resultlist as resultlist

from .config import build_config, Config
from .constants import CONFIG_FILENAME
from .deploy import deploy_results
from .container import run_self_in_container
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

    p.add_argument(
        "files",
        nargs="*",
        help=(
            f"Main songbook files to compile (overrides songbooks defined in {CONFIG_FILENAME}). "
            f"Alternatively, give a single project directory or a single existing {CONFIG_FILENAME} "
            "file to select the project root without specifying explicit documents. If none of these "
            "are given, the current working directory is assumed to be the project directory."
        ),
    )

    p.add_argument("-q", "--quick", action="store_true", help="Quick dev build: default variant only, no extras, no deploy, keep temp")
    p.add_argument("-v", "--verbose", action="store_true", help="Verbose output")

    p.add_argument("-p", "--profile", default="default", help=f"Choose profile defined in {CONFIG_FILENAME} to use")

    p.add_argument(
        "--container-engine",
        choices=["auto", "docker", "podman"],
        help=(
            "Container engine to use: 'auto' (default, prefer Docker then Podman), "
            "'docker' (require Docker), or 'podman' (require Podman)"
        ),
    )
    p.add_argument("--container-rebuild", action="store_true", help="Force rebuilding of container image")
    p.add_argument("--no-container", dest="no_container", action="store_true", help="Compile on host instead of using a container (not recommended)")
    p.add_argument("--pull", action="store_true", help="Run 'git pull --rebase' before compiling")
    p.add_argument("--sequential", action="store_true", help="Do not compile in parallel (to conserve memory)")
    p.add_argument("--max-parallel", type=int, metavar="N", default=0, help="Maximum number of parallel jobs (0 = auto)")
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
    prestr.add_argument("--fast-audio-encode", dest="fast_audio_encode", action="store_true", help="Use faster audio encoding (limiter instead of loudnorm)")
    prestr.add_argument("--midifiles-allow-for-optional-variants", action="store_true", help="Allow MIDI file generation for optional variants")
    prestr.add_argument("--audiofiles-allow-for-optional-variants", action="store_true", help="Allow audio file generation for optional variants")

    pmodes = p.add_argument_group("special modes")
    pmodes.add_argument("--shell", action="store_true", help="Only open an interactive shell in the container; perform no other actions")
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

    ui.plain("")
    ui.plain(ui.colorize(f"{'Compiling a songbook:' if songbooks_count == 1 else 'Compiling songbooks:'}", ui.C_WHITE))
    ui.plain("")
    ui.plain(f"  - Project root: {ui.colorize(cfg.runtime.project_paths.host_project_root, ui.C_LBLUE)}")
    ui.plain(f"  - Base profile: {ui.colorize(cfg.profile, ui.C_LBLUE)}")
    ui.plain(f"  - Songbooks to compile: {ui.colorize(f'{songbooks_count}', ui.C_LBLUE)} {ui.colorize(f'({jobs_count} variant jobs)', ui.C_BLUE)}")
    ui.plain(f"  - Using container: {_yn(cfg.use_container or cfg.runtime.in_container)}"
      + (f" {ui.colorize(f'(engine: {cfg.container_engine})', ui.C_BLUE)})" if (cfg.use_container or cfg.runtime.in_container) else f" {ui.C_YELLOW}(this is not recommended!){ui.C_RESET}"))
    ui.plain(f"  - Parallel compilation: {_yn(cfg.max_parallel > 1)}" + ui.colorize(f" ({cfg.max_parallel} workers)" if cfg.max_parallel > 1 else "", ui.C_BLUE))
    ui.plain(f"  - Using system's /tmp for temp: {_yn(cfg.use_system_tmp)}")
    ui.plain(f"  - Clean up temp after successful compilation: {_yn(cfg.clean_temp)}")
    ui.plain(f"  - Additional lyrics only variants: {_yn(cfg.lyricbooks)}")
    ui.plain(f"  - Additional extra instrument variants: {_yn(cfg.extrainstrumentbooks)}")
    ui.plain(f"  - Create printouts: {_yn(cfg.create_printouts)}")
    ui.plain(f"  - Extract covers as images: {_yn(cfg.coverimage)}")
    ui.plain(f"  - Create MIDI files: {_yn(cfg.midifiles)}")
    if cfg.midifiles:
        ui.plain(f"    - Also for optional variants: {_yn(cfg.midifiles_allow_for_optional_variants)}")
    ui.plain(f"  - Create audio files: {_yn(cfg.audiofiles)}")
    if cfg.audiofiles:
        ui.plain(f"    - Also for optional variants: {_yn(cfg.audiofiles_allow_for_optional_variants)}")
        ui.plain(f"    - Fast audio encode (no loudnorm): {_yn(cfg.fast_audio_encode)}")
    ui.plain(f"  - Deploy: {_yn(cfg.deploy)}")
    ui.plain("")


def main(argv: List[str] | None = None) -> int:
    """CLI entrypoint. Returns process exit code."""

    def post_compile():
        """
        Does post-compile actions that need to be done on the host:
          - deploy
        """
        if cfg.runtime.in_container:
            return
        # Use resultlist in result location
        resultlist.initialize(proj.result_dir, unique_id)
        if cfg.deploy and not cfg.shell:
            ui.plain("")
            deploy_results(ui=ui, cfg=cfg)
        ui.plain("")

    ui = UI(use_colors=True)
    assets = EngineAssets()
    ns = build_arg_parser(ui=ui).parse_args(argv)

    # Interpret positional arguments:
    #   - no args: use CWD as project root (handled by ProjectPaths.from_docs)
    #   - single directory: treat it as explicit project root
    #   - single existing CONFIG_FILENAME: its parent is the project root
    #   - otherwise: treat all arguments as explicit document files and infer
    #     project root from their common ancestor containing CONFIG_FILENAME.
    #
    # Mixing a directory/config with explicit documents is not allowed.
    raw_paths = [Path(x) for x in ns.files]
    explicit_docs: list[Path] = []
    root_override: Path | None = None
    root_override_arg: str | None = None

    if not raw_paths:
        explicit_docs = []
    elif len(raw_paths) == 1:
        p = raw_paths[0]
        # Single directory: use as explicit project root
        if p.is_dir():
            root_override = p.resolve()
            root_override_arg = ns.files[0]
            ns.files = []  # No explicit documents
        # Single existing config file: use its parent as project root
        elif p.name == CONFIG_FILENAME and p.is_file():
            root_override = p.resolve().parent
            root_override_arg = ns.files[0]
            ns.files = []  # No explicit documents
        else:
            explicit_docs = raw_paths
    else:
        # Multiple positional arguments: reject if any is a directory or
        # an existing config file, since that would mix project-root
        # selection with explicit documents.
        def _is_root_selector(path: Path) -> bool:
            return path.is_dir() or (path.name == CONFIG_FILENAME and path.is_file())

        if any(_is_root_selector(p) for p in raw_paths):
            ui.plain("")
            ui.error_line("Invalid arguments: cannot mix a project directory or config file with explicit document files.")
            ui.space_line("Give either a single directory/config to select the project, or one or more document files.")
            ui.plain("")
            return 1
        explicit_docs = raw_paths

    if root_override is not None:
        proj = ProjectPaths.from_root(root_override)
    else:
        proj = ProjectPaths.from_docs(explicit_docs)

    in_container = bool(os.environ.get("ULSBS_INTERNAL_RUNNING_IN_CONTAINER"))
    unique_id = os.environ.get("ULSBS_INTERNAL_UNIQUE_ID", create_unique_id()) or create_unique_id()

    try:
        cfg = build_config(
            profile=getattr(ns, "profile", "default"),
            args_ns=ns,
            config_path=proj.config_file,
            env=os.environ,
            runtime_project_paths=proj,
            runtime_in_container=in_container,
            runtime_unique_id=unique_id,
            ui=ui,
        )
    except Exception as e:
        ui.plain("")
        ui.error_line("Configuration error!")
        ui.space_line(f"Config file: {proj.config_file}")
        ui.space_line(ui.colorize(e, ui.C_YELLOW))
        ui.plain("")
        return 1

    # Deploy-only modes use CWD as project root and are run outside container
    if cfg.deploy_last or cfg.deploy_common:
        mode_text = "Common files only" if cfg.deploy_common else "Latest results"
        ui.plain("")
        ui.plain(ui.colorize("Deploying existing files:", ui.C_WHITE))
        ui.plain("")
        ui.plain(f"  - Project root: {ui.colorize(cfg.runtime.project_paths.project_root, ui.C_LBLUE)}")
        ui.plain(f"  - Mode: {ui.colorize(mode_text, ui.C_LBLUE)}")
        ui.plain("")
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
        ui.plain("")
        return 0

    # Host-only git pull
    if cfg.pull and not cfg.in_container:
        if which("git") is None:
            raise SystemExit("'git' binary not found in PATH, but pull requested!")
        ui.git_line("Pulling remote changes (with rebase)...")
        run_cmd(["git", "pull", "--rebase"], cwd=cfg.runtime.project_paths.project_root, check=True)

    # Host-only temp dir setup
    if not cfg.runtime.in_container:
        setup_temp_dir(ui, cfg)

    # Container (default) unless --no-container
    if cfg.use_container and not cfg.runtime.in_container:
        passthrough = (argv if argv is not None else os.sys.argv[1:])

        # If a single directory or config file was used to select the project
        # root, drop that argument when invoking the inner CLI: inside the
        # container the project root is already the working directory.
        if root_override_arg is not None:
            passthrough = [a for a in passthrough if a != root_override_arg]

        # Rebase explicit document arguments to be relative to the project root
        # so that they resolve correctly inside the Docker container, where the
        # project root is mounted at a fixed path.
        if ns.files:
            rebased_docs: list[str] = []
            for orig, doc_path in zip(ns.files, explicit_docs, strict=True):
                try:
                    rel = doc_path.resolve().relative_to(proj.project_root)
                except ValueError:
                    # If the document is not under the project root, fall back
                    # to the original argument string.
                    rel = Path(orig)
                rebased_docs.append(str(rel))
            doc_map = {orig: new for orig, new in zip(ns.files, rebased_docs, strict=True)}
            passthrough = [doc_map.get(a, a) for a in passthrough]

        try:
            rc = run_self_in_container(
                ui=ui,
                assets=assets,
                cfg=cfg,
                passthrough_args=list(passthrough),
                script_file=Path(__file__),
            )
        except Exception as ex:
            ui.error_line(f"Error: {ex}")
            return 1

        # Host-side post-actions (deploy) after container finishes
        if rc == 0:
            post_compile()

        return rc

    # Shell-only mode
    if cfg.shell:
        ui.exec_line("Start interactive shell")
        os.execvp("bash", ["bash"])
        return 127

    if cfg.verbose:
        total_mem = f"{str(cfg.runtime.system_info.total_mem_gb or '?')} GiB"
        free_mem = f"{str(cfg.runtime.system_info.free_mem_gb or '?')} GiB"
        threads = str(cfg.runtime.system_info.cpu_threads or '?')
        ui.info_line(f"SYSTEM - cpu threads: {threads}, free memory: {free_mem}, total memory: {total_mem}")

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

        ui.plain("")
        ui.abort_line(ui.colorize("All unfinished jobs aborted by user intervention.", ui.C_YELLOW))
        ui.plain("")

        return 130

    resultlist.finalize(dst_dir=proj.result_dir, runresult=result, delete_existing_resultlists_in_dst=True)

    if cfg.clean_temp and not result.failures:
        try:
            if clear_temp_dir_if_no_locks(proj.temp_dir):
                ui.info_line("Temp cleared")
            else:
                ui.info_line("Temp not cleared due to other jobs still running")
        except Exception as e:
            ui.warning_line(f"Temp not cleared due to an error: {str(e)}")
    else:
        ui.info_line("Temp is kept.")

    if result.successes:
        ui.plain("")
        ui.success_line(f"{'All' if len(result.successes) == len(jobs) else len(result.successes)} jobs succeeded.")
        if result.total_warnings:
            ui.warning_line(f"Tools' output logs contained a total of {result.total_warnings} warnings for all jobs together.")
            if cfg.clean_temp:
                ui.space_line("To keep the logs for analyzing them, run with --keep-temp")

    if result.failures:
        ui.plain("")
        ui.fail_line(f"{'All' if len(result.failures) == len(jobs) else 'Some'} jobs failed:")
        for f in result.failures:
            ui.fail_line(f"  - {f.job.doc_stem}:{f.job.variant} -> {f.reason}")
        if cfg.deploy:
            ui.plain("")
            ui.nodeploy_line("Nothing is deployed due to failures.")
        ui.plain("")
        return 1

    if not cfg.runtime.in_container:
         post_compile()

    return 0
