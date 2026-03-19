# SPDX-FileCopyrightText: 2016-2026 Lari Natri <lari.natri@iki.fi>
# SPDX-License-Identifier: GPL-3.0-or-later

"""
Compilation pipeline: prepare, run tools, and post-process outputs.
This file is part of the 'ulsbs' package.
"""

from __future__ import annotations

import concurrent.futures as cf
import os
import re
import shlex
import shutil
import signal
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import List
from fnmatch import fnmatch

from .config import Config
from .constants import (
    LYRICSONLY_FNAMEPART, CHARANGO_FNAMEPART, BASSCLEF_FNAMEPART,
    PAPERA5_FNAMEPART,
    RESULT_TYPE_MAIN_PDF, RESULT_TYPE_PRINTOUT_PDF, RESULT_TYPE_IMAGE,
    RESULT_TYPE_MIDIDIR, RESULT_TYPE_AUDIODIR,
    RESULT_PRINTOUT_SUBDIRNAME, RESULT_IMAGE_SUBDIRNAME,
    RESULT_MIDI_SUBDIRNAME, RESULT_AUDIO_SUBDIRNAME,
    SONG_IDX_SCRIPT_REL, SORT_LOCALE,
    COVERIMAGE_MODIFIED_FNAME_POSTFIX,
    SELECTION_FNAME_PREFIX,
    TEMP_DIRNAME, CONTENT_DIRNAME, INCLUDE_DIRNAME, TAG_DEFINITION_FILENAME,
    GENAUDIO_ALBUMTITLE,
)
from .engine_assets import EngineAssets
from .jobs import Job, build_variant_basename
from .lock import JobLock
from .songdb import build_song_database, SongbookData
import ulsbs.resultlist as resultlist
from .ui import UI
from .util import (
    ensure_dir,
    ensure_symlink,
    read_text,
    run_cmd,
    safe_rm_tree,
    overlay_tree,
    symlink_tree,
    which,
    write_text,
    append_text,
    regex_documentclass_ulsbs_songbook,
)

_JOB_ULSBS_ASSETS_DIRNAME = "ulsbs-assets"

ABORT_EVENT = threading.Event()


class CompileError(RuntimeError):
    """Error during a compile step; may carry a path to a log file."""
    def __init__(self, message: str, log_path: Path | None = None):
        super().__init__(message)
        self.log_path = log_path


# Result containers for parallel runs
@dataclass(frozen=True)
class JobSuccess:
    job: Job
    warning_count: int

@dataclass(frozen=True)
class JobFailure:
    job: Job
    reason: str

@dataclass
class ParallelRunResult:
    successes: List[JobSuccess]
    failures: List[JobFailure]
    total_warnings: int = 0


def die_log(ui: UI, cfg: Config, job: Job, cwd: Path, message: str, log_path: Path | None) -> None:
    """
    Show an error and tail a log (if any), then raise CompileError.
    Intended to be called when a step fails within a job.
    """
    if ABORT_EVENT.is_set():
        # Quiet abort: no log spam
        raise KeyboardInterrupt()

    txt_doc = ui.fmt_doc(f"{job.doc_stem}:{job.variant}", job.color)
    ui.error_line(f"{txt_doc}: {message}")
    if log_path is not None:
        try:
            rel = cwd.relative_to(cfg.runtime.project_paths.project_root)
            ui.see_line(f"{ui.C_YELLOW}{rel}/{log_path.name}{ui.C_RESET}")
        except Exception:
            pass
        if cfg.max_log_lines > 0:
            ui.plain("")
            ui.space_line(ui.colorize(f"Displaying the last {cfg.max_log_lines} lines of log:", ui.C_YELLOW))
            ui.plain("")
            try:
                from collections import deque
                with log_path.open("r", encoding="utf-8", errors="replace") as f:
                    tail = deque(f, maxlen=cfg.max_log_lines)
                ui.plain("".join(tail))
            except Exception:
                ui.warning("(Could not read log)")
    else:
        ui.warning("(No log file available)")
    raise CompileError(message, log_path)


def require_tools() -> None:
    """Ensure required external tools are available in PATH."""
    for t in ("lualatex", "texlua", "lilypond-book"):
        if which(t) is None:
            raise SystemExit(f"'{t}' binary not found in PATH")


def build_tool_include_paths(job: Job) -> tuple[dict[str, str], list[str]]:
    """
    Construct include paths for TeX/LuaTeX and LilyPond for the job.

    Returns (env, lp_args) where env has TEXINPUTS/LUAINPUTS, and lp_args
    are -I include dirs for lilypond/lilypond-book.
    """
    # Start from a copy of the current environment so we only augment it.
    env = os.environ.copy()

    # Compute path roots used by tools.
    job_root = str(job.compile_dir)          # Job's working directory
    job_ulsbs_tex = str(job.compile_dir / _JOB_ULSBS_ASSETS_DIRNAME / "tex")  # ULSBS TeX tree within the job
    job_ulsbs_lp = str(job.compile_dir / _JOB_ULSBS_ASSETS_DIRNAME / "ly")    # LilyPond includes live under ly/
    job_content = str(job.compile_dir / CONTENT_DIRNAME)
    job_include = str(job.compile_dir / INCLUDE_DIRNAME)

    # TeX engine search paths (colon-separated). Trailing ':' keeps defaults.
    tex_path_prefix = f"{job_root}:{job_content}:{job_include}:{job_ulsbs_tex}:"
    env["TEXINPUTS"] = tex_path_prefix + env.get("TEXINPUTS", "")
    env["LUAINPUTS"] = tex_path_prefix + env.get("LUAINPUTS", "")

    # LilyPond search paths.
    lp_args = ["-I", job_root, "-I", job_ulsbs_lp]

    return env, lp_args


def prepare_compile_dir(ui: UI, assets: EngineAssets, cfg: Config, job: Job) -> None:
    """Create job workdir and populate assets, aliases, and content links."""
    ensure_dir(job.compile_dir / _JOB_ULSBS_ASSETS_DIRNAME)

    # tex tree from ulsbs (copied, because variants modify some files)
    ensure_dir(job.compile_dir / _JOB_ULSBS_ASSETS_DIRNAME / "tex")
    with assets.tex_dir() as src_tex:
        shutil.copytree(src_tex, job.compile_dir / _JOB_ULSBS_ASSETS_DIRNAME / "tex", dirs_exist_ok=True)

    # ly tree from ulsbs (copied, because variants modify some files)
    ensure_dir(job.compile_dir / _JOB_ULSBS_ASSETS_DIRNAME / "ly")
    with assets.ly_dir() as src_ly:
        shutil.copytree(src_ly, job.compile_dir / _JOB_ULSBS_ASSETS_DIRNAME / "ly", dirs_exist_ok=True)

    # img tree from ulsbs (copied, because variants modify some files)
    ensure_dir(job.compile_dir / _JOB_ULSBS_ASSETS_DIRNAME / "img")
    with assets.img_dir() as src_img:
        shutil.copytree(src_img, job.compile_dir / _JOB_ULSBS_ASSETS_DIRNAME / "img", dirs_exist_ok=True)

    # Aliases
    ensure_symlink(
        job.compile_dir / "ulsbs" / "assets",
        job.compile_dir / _JOB_ULSBS_ASSETS_DIRNAME,
        fallback_copy=True,
    )
    ensure_symlink(
        job.compile_dir / "ulsbs" / "src" / "ulsbs" / "assets",
        job.compile_dir / _JOB_ULSBS_ASSETS_DIRNAME,
        fallback_copy=True,
    )

    # content tree (symlink all files)
    dst_content = job.compile_dir / CONTENT_DIRNAME
    if cfg.runtime.project_paths.content_dir.exists():
        ensure_dir(dst_content)
        symlink_tree(cfg.runtime.project_paths.content_dir, dst_content, fallback_copy=True)

    # include tree (symlink all files)
    dst_include = job.compile_dir / INCLUDE_DIRNAME
    if cfg.runtime.project_paths.include_dir.exists():
        ensure_dir(dst_include)
        symlink_tree(cfg.runtime.project_paths.include_dir, dst_include, fallback_copy=True)


def make_variant_tex(job: Job) -> Path:
    """Create variant .tex in the job dir, injecting post-setup if needed."""
    src = job.doc_tex_abs
    txt = read_text(src)

    if job.variant == "default":
        out_path = job.compile_dir / src.name
        shutil.copy2(src, out_path)
        return out_path

    if job.variant == "lyrics":
        docclass_re = regex_documentclass_ulsbs_songbook()
        injected = docclass_re.sub(
            lambda m: m.group(0) + "\n\\input{ulsbs-internal-lyricbook-postsetup.tex}",
            txt,
            count=1,
        )
        out_name = build_variant_basename(job.doc_stem, LYRICSONLY_FNAMEPART) + ".tex"
        out_path = job.compile_dir / out_name
        write_text(out_path, injected)
        return out_path

    if job.variant == "charango":
        docclass_re = regex_documentclass_ulsbs_songbook()
        injected = docclass_re.sub(
            lambda m: m.group(0) + "\n\\input{ulsbs-internal-charangobook-postsetup.tex}",
            txt,
            count=1,
        )
        out_name = build_variant_basename(job.doc_stem, CHARANGO_FNAMEPART) + ".tex"
        out_path = job.compile_dir / out_name
        write_text(out_path, injected)

        head = job.compile_dir / _JOB_ULSBS_ASSETS_DIRNAME / "ly" / "ulsbs-internal-common-head.ly"
        if head.exists():
            head_txt = read_text(head).replace(
                "ul-chosen-tuning = #ul-guitar-tuning",
                "ul-chosen-tuning = #ul-charango-tuning",
            )
            write_text(head, head_txt)
        return out_path

    if job.variant == "bassclef":
        docclass_re = regex_documentclass_ulsbs_songbook()
        injected = docclass_re.sub(
            lambda m: m.group(0) + "\n\\input{ulsbs-internal-bassclefbook-postsetup.tex}",
            txt,
            count=1,
        )
        out_name = build_variant_basename(job.doc_stem, BASSCLEF_FNAMEPART) + ".tex"
        out_path = job.compile_dir / out_name
        write_text(out_path, injected)

        for f in (job.compile_dir / _JOB_ULSBS_ASSETS_DIRNAME / "ly").glob("ulsbs-include-tail*_bassclef.ly"):
            newname = f.name.replace("_bassclef", "")
            shutil.copy2(f, job.compile_dir / _JOB_ULSBS_ASSETS_DIRNAME / "ly" / newname)
        return out_path

    raise SystemExit(f"Unknown variant: {job.variant}")




def run_lilypond_book(ui: UI, proj_content_dir: Path, job: Job, input_tex: Path, env: dict[str, str], lp_include_args: list[str], step: int) -> tuple[Path, Path, int]:
    """
    Run lilypond-book in the job directory, but output into a dedicated subdir
    to avoid "Output would overwrite input file" errors.

    Returns:
      - Path to the processed .tex in the job root (after overlay-moving _lp)
      - Path to the lilypond-book log
      - Next step number
    """
    txt_doc = ui.fmt_doc(f"{job.doc_stem}:{job.variant}", job.color)
    lp_out = job.compile_dir / "_lp"
    ensure_dir(lp_out)

    log_path = job.compile_dir / f"log-{step:02d}_lilypond.log"
    ui.exec_line(f"{txt_doc}: {ui.fmt_step(step)} lilypond-book")

    # We run in the job dir, and pass the input file name (must be present there).
    cwd = job.compile_dir
    input_arg = input_tex.name

    process_cmd = shlex.join(["lilypond", *lp_include_args, "-dno-point-and-click"])
    args = [
        "lilypond-book",
        "-f", "latex",
        "--latex-program=lualatex",
        "--pdf",
        f"--process={process_cmd}",
        "--output", str(lp_out),
        "--use-source-file-names",
        input_arg,
    ]

    try:
        run_cmd(args, cwd=cwd, stdout_path=log_path, stderr_to_stdout=True, check=True, env=env)
    except Exception:
        if ABORT_EVENT.is_set():
            raise KeyboardInterrupt()
        raise CompileError("lilypond-book failed", log_path)

    # lilypond-book produces a processed TeX file into lp_out, typically with the same basename
    produced = lp_out / input_tex.name
    if not produced.exists():
        # Be tolerant if lilypond-book slightly changes naming
        candidates = sorted(lp_out.glob(f"{input_tex.stem}*.*tex"))
        if candidates:
            produced = candidates[0]
        else:
            raise CompileError("lilypond-book did not produce expected .tex", log_path)

    # Overlay-move everything lilypond-book produced in job/_lp into the job root.
    overlay_tree(lp_out, job.compile_dir, move=True)
    try:
        safe_rm_tree(lp_out)
    except Exception:
        pass

    processed_in_jobroot = job.compile_dir / produced.name
    return processed_in_jobroot, log_path, step + 1


def run_lualatex_pass(ui: UI, cfg: Config, job: Job, basename: str, env: dict[str, str], step: int, pass_no: int, draftmode: bool) -> tuple[Path, int]:
    """Run a LuaLaTeX pass and return the log path and next step number."""
    cwd = job.compile_dir
    txt_doc = ui.fmt_doc(f"{job.doc_stem}:{job.variant}", job.color)
    log_path = cwd / f"log-{step:02d}_lualatex-pass{pass_no}.log"
    label = f"lualatex (pass {pass_no})"
    ui.exec_line(f"{txt_doc}: {ui.fmt_step(step)} {label}")
    args = [
        "lualatex",
        "-file-line-error",
        "-halt-on-error",
        "-interaction=nonstopmode",
    ]
    if draftmode:
        args.append("-draftmode")
    args.append(f"{basename}.tex")

    try:
        run_cmd(args, cwd=cwd, stdout_path=log_path, stderr_to_stdout=True, check=True, env=env)
    except Exception:
        raise CompileError(f"Compilation error running {label}!", log_path)

    return log_path, step + 1


def run_texlua_indices(ui: UI, cfg: Config, job: Job, basename: str, env: dict[str, str], step: int) -> int:
    """Create title and tag indices using texlua scripts."""
    cwd = job.compile_dir
    txt_doc = ui.fmt_doc(f"{job.doc_stem}:{job.variant}", job.color)

    # Find script
    song_idx_script = cwd / SONG_IDX_SCRIPT_REL
    if not song_idx_script.exists():
        song_idx_script = cwd / _JOB_ULSBS_ASSETS_DIRNAME / "tex" / "ext_packages" / "songs" / "songidx.lua"
    if not song_idx_script.exists():
        msg = f"songidx.lua not found at {song_idx_script}"
        logp = cwd / f"log-{step:02d}_indices-error.log"
        write_text(logp, msg)
        raise CompileError(msg, logp)

    # Title index
    log_title = cwd / f"log-{step:02d}_titleidx.log"
    ui.exec_line(f"{txt_doc}: {ui.fmt_step(step)} texlua (create title index)")
    try:
        run_cmd(["texlua", str(song_idx_script), "-l", SORT_LOCALE, "idx_title.sxd", "idx_title.sbx"],
                cwd=cwd, stdout_path=log_title, stderr_to_stdout=True, check=True, env=env)
    except Exception:
        raise CompileError("Error creating song title indices!", log_title)
    step += 1

    # Tag index
    if (cwd / INCLUDE_DIRNAME / TAG_DEFINITION_FILENAME).exists():
        log_tag = cwd / f"log-{step:02d}_tagidx.log"
        ui.exec_line(f"{txt_doc}: {ui.fmt_step(step)} texlua (create tag index)")
        try:
            run_cmd(["texlua", str(song_idx_script), "-l", SORT_LOCALE, "-b", str(INCLUDE_DIRNAME + "/" + TAG_DEFINITION_FILENAME), "idx_tag.sxd", "idx_tag.sbx"],
                    cwd=cwd, stdout_path=log_tag, stderr_to_stdout=True, check=True, env=env)
        except Exception:
            raise CompileError("Error creating tag indices!", log_tag)
        step += 1
    else:
        ui.warning_line("Skipping creating tag index: tag definition file not found!")
    return step


def run_context_printouts(ui: UI, cfg: Config, job: Job, basename: str, env: dict[str, str], step: int) -> int:
    """Create extra A5-on-A4 printouts with ConTeXt if templates exist."""
    result_dir = cfg.runtime.project_paths.result_dir
    cwd = job.compile_dir
    txt_doc = ui.fmt_doc(f"{job.doc_stem}:{job.variant}", job.color)

    if PAPERA5_FNAMEPART not in basename or not cfg.create_printouts:
        return step

    context_bin = which("context") or which("contextjit")
    if not context_bin:
        ui.noexec_line(f"{txt_doc}: Extra printout PDFs not created; no 'context/contextjit'")
        return step

    ui.exec_line(f"{txt_doc}: {ui.fmt_step(step)} context (create printouts)")
    ensure_dir(result_dir / RESULT_PRINTOUT_SUBDIRNAME)

    def make_printout(template: Path, out_base: str, step: int) -> int:
        """Render a ConTeXt template and copy result to result/printouts."""
        if not template.exists():
            ui.noexec_line(f"{txt_doc}: Printout template missing: {template.name}")
            return step
        ctx_out = cwd / f"{out_base}.context"
        data = read_text(template).replace("REPLACE-THIS-FILENAME.pdf", f"{basename}.pdf")
        write_text(ctx_out, data)
        logp = cwd / f"log-{step:02d}_context-{out_base}.log"
        try:
            run_cmd([context_bin, ctx_out.name], cwd=cwd, stdout_path=logp, stderr_to_stdout=True, check=True, env=env)
        except Exception:
            raise CompileError(f"context failed for {out_base}", logp)
        pdf_out = cwd / f"{out_base}.pdf"
        if pdf_out.exists():
            shutil.copy2(pdf_out, result_dir / RESULT_PRINTOUT_SUBDIRNAME / pdf_out.name)
            resultlist.append_line(RESULT_TYPE_PRINTOUT_PDF, pdf_out.name)
        return step + 1

    tpl1 = cwd / _JOB_ULSBS_ASSETS_DIRNAME / "tex" / "ulsbs-printout-template_BOOKLET-A5-on-A4-doublesided-needs-cutting.context"
    tpl2 = cwd / _JOB_ULSBS_ASSETS_DIRNAME / "tex" / "ulsbs-printout-template_EASY-A5-on-A4-sidebyside-simple.context"

    step = make_printout(tpl1, f"printout-BOOKLET_{basename}-on-A4-doublesided-needs-cutting", step)
    step = make_printout(tpl2, f"printout-EASY_{basename}-on-A4-sidebyside-simple", step)

    return step


def run_coverimage_extraction(ui: UI, cfg: Config, job: Job, basename: str, env: dict[str, str], step: int) -> int:
    """Extract cover image(s) from the compiled PDF using pdftoppm/convert.

    The extracted base PNG is always created. Optionally, a modified/widened
    PNG is created using ImageMagick convert, driven by cfg.modified_cover_png
    rules that match the original TeX filename (job.doc_tex_abs.name).
    """
    result_dir = cfg.runtime.project_paths.result_dir
    cwd = job.compile_dir
    txt_doc = ui.fmt_doc(f"{job.doc_stem}:{job.variant}", job.color)

    if not cfg.coverimage or not which("pdftoppm"):
        return step

    ensure_dir(result_dir / RESULT_IMAGE_SUBDIRNAME)

    # Extract cover as PNG with configurable height
    ui.exec_line(f"{txt_doc}: {ui.fmt_step(step)} pdftoppm (extract cover as image)")
    log_extract = cwd / f"log-{step:02d}_coverimage-extract.log"
    try:
        run_cmd([
            "pdftoppm",
            "-f", "1",
            "-singlefile",
            "-png",
            "-scale-to-x", "-1",
            "-scale-to-y", str(cfg.cover_image_height),
            f"{basename}.pdf",
            basename,
        ], cwd=cwd, stdout_path=log_extract, stderr_to_stdout=True, check=True, env=env)
    except Exception:
        raise CompileError("pdftoppm failed while extracting cover image", log_extract)
    step += 1

    cover_png = cwd / f"{basename}.png"
    if cover_png.exists():
        shutil.copy2(cover_png, result_dir / RESULT_IMAGE_SUBDIRNAME / cover_png.name)
        resultlist.append_line(RESULT_TYPE_IMAGE, cover_png.name)

    # Optional: create auto-wide image via ImageMagick convert
    if which("convert"):
        ui.exec_line(f"{txt_doc}: {ui.fmt_step(step)} convert (cover image modified)")
        cover_modified_png = cwd / f"{basename}{COVERIMAGE_MODIFIED_FNAME_POSTFIX}.png"
        log_auto = cwd / f"log-{step:02d}_coverimage-modified.log"

        # Probe image size using ImageMagick so we can interpret fractional rects
        try:
            run_cmd(
                ["convert", cover_png.name, "-format", "%w %h", "info:"],
                cwd=cwd,
                stdout_path=log_auto,
                stderr_to_stdout=True,
                check=True,
                env=env,
            )
            tokens = read_text(log_auto).split()
            if len(tokens) < 2:
                raise ValueError("Unexpected output from convert -format '%w %h'")
            img_w = int(tokens[0])
            img_h = int(tokens[1])
        except Exception:
            raise CompileError("convert failed while probing cover image size", log_auto)

        # Select the last matching rule (if any) based on the original TeX filename
        src_filename = job.doc_tex_abs.name
        selected_rule = None
        for rule in cfg.modified_cover_png:
            if fnmatch(src_filename, rule.songbook_filenames):
                selected_rule = rule

        cmd: list[str] = ["convert", cover_png.name]

        if selected_rule is not None:
            rule = selected_rule
            # Optional painting on the original image before widening
            rects = list(rule.paint_area_rects)
            if rects:
                cmd += ["-fill", rule.color]
                for r in rects:
                    # Bottom-left (0,0) -> ImageMagick's top-left (0,0)
                    x1 = int(round(r.x1 * img_w))
                    x2 = int(round(r.x2 * img_w))
                    y1 = int(round((1.0 - r.y2) * img_h))
                    y2 = int(round((1.0 - r.y1) * img_h))
                    cmd += ["-draw", f"rectangle {x1},{y1} {x2},{y2}"]

            # Width relative to original; 0 means "square" (width = height)
            target_h = img_h
            if rule.width_multiplier == 0:
                target_w = target_h
            else:
                target_w = int(round(img_w * rule.width_multiplier))

            cmd += [
                "-background", rule.color,
                "-gravity", "center",
                "-extent", f"{target_w}x{target_h}",
                cover_modified_png.name,
            ]
        else:
            # No specific rule; make the modified image a square and center
            # the image, without extra painting.
            target_w = target_h = img_h
            cmd += [
                "-gravity", "center",
                "-extent", f"{target_w}x{target_h}",
                cover_modified_png.name,
            ]

        try:
            run_cmd(
                cmd,
                cwd=cwd,
                stdout_path=log_auto,
                stderr_to_stdout=True,
                check=True,
                env=env,
                append=True,
            )
        except Exception:
            raise CompileError("convert failed while creating modified cover image", log_auto)

        if cover_modified_png.exists():
            shutil.copy2(cover_modified_png, result_dir / RESULT_IMAGE_SUBDIRNAME / cover_modified_png.name)
            resultlist.append_line(RESULT_TYPE_IMAGE, cover_modified_png.name)
        step += 1

    return step


def build_song_db(
    ui: UI,
    cfg: Config,
    job: Job,
    processed_tex: Path,
    step: int,
) -> tuple[SongbookData | None, int]:
    """Build the song database from the processed TeX tree."""
    txt_doc = ui.fmt_doc(f"{job.doc_stem}:{job.variant}", job.color)
    log_path = job.compile_dir / f"log-{step:02d}_songdb.log"

    # Skip if midi nor audio is requested
    if not (cfg.midifiles or cfg.audiofiles):
        return None, step
    # Skip if this is an optional variant and neither audio nor midi is allowed for optional variants
    if job.variant != "default" and not (cfg.midifiles_allow_for_optional_variants or cfg.audiofiles_allow_for_optional_variants):
        return None, step

    ui.exec_line(f"{txt_doc}: {ui.fmt_step(step)} internal: build song tree")

    # Do not include the project's tex path, as those files are not needed to
    # be parsed for our songs db.
    search_paths = [
        job.compile_dir,
        job.compile_dir / CONTENT_DIRNAME,
        job.compile_dir / INCLUDE_DIRNAME,
    ]
    try:
        db = build_song_database(processed_tex=processed_tex, include_search_paths=search_paths, variant=job.variant)
        write_text(
            log_path,
            "Internal song database built for this book.\n\n"
            f"  - Book title: {'<none>' if db.book_info.maintitle == None else db.book_info.maintitle}\n"
            f"  - Book subtitle: {'<none>' if db.book_info.subtitle == None else db.book_info.subtitle}\n"
            f"  - Book variant: {'<none>' if db.book_info.variant == None else db.book_info.variant}\n"
            f"  - Total songs found: {str(db.total_songs)}\n\n"
        )
    except Exception as e:
        write_text(log_path, f"Song database build failed: {e!r}\n")
        raise CompileError("Failed to build song/chapter data from TeX", log_path)
    step += 1
    return db, step


def run_midi_audio(
    ui: UI,
    assets: EngineAssets,
    cfg: Config,
    job: Job,
    processed_tex: Path,
    db: SongbookData | None,
    step: int,
) -> int:
    """Create MIDI directories and audio encodes based on the TeX tree."""

    do_midi: bool = cfg.midifiles
    do_audio: bool = cfg.audiofiles

    # Skip if no midi nor audio is requested
    if not (do_midi or do_audio):
        return step

    if job.variant != "default":
        do_midi = cfg.midifiles_allow_for_optional_variants
        do_audio = cfg.audiofiles_allow_for_optional_variants

    # Skip if no midi nor audio is allowed for this (optional) variant
    if not (do_midi or do_audio):
        return step

    txt_doc = ui.fmt_doc(f"{job.doc_stem}:{job.variant}", job.color)

    if db is None:
        ui.warning_line(f"{txt_doc}: No internal db; skipping midi/audio")
        return step

    result_dir = cfg.runtime.project_paths.result_dir

    # Flatten songs while keeping document order
    all_songs = list(db.songs_without_chapter)
    for chap in db.chapters:
        all_songs.extend(chap.songs)
    songs_with_midi = [s for s in all_songs if s.midi_abs_path is not None]

    if not songs_with_midi:
        ui.noexec_line(f"{txt_doc}: No MIDI files referenced; skipping midi/audio")
        return step

    # MIDI copies
    if do_midi:
        ui.exec_line(f"{txt_doc}: {ui.fmt_step(step)} internal: grab MIDI files")
        cur_res_midi = result_dir / RESULT_MIDI_SUBDIRNAME / processed_tex.stem
        safe_rm_tree(cur_res_midi)
        ensure_dir(cur_res_midi)
        log_midi = job.compile_dir / f"log-{step:02d}_grab-midi.log"
        copy_error_count = 0

        for song in songs_with_midi:
            parent = cur_res_midi
            if song.chapter_slug:
                parent = parent / song.chapter_slug
            ensure_dir(parent)

            if song.number is not None:
                num_str = f"{song.number:03d}"
            else:
                # Fallback to order index if counter is unavailable
                num_str = f"{song.order_index:03d}"
            base = f"{num_str}__{song.title_slug}"
            dest = parent / f"{base}.midi"
            try:
                shutil.copy2(song.midi_abs_path, dest)
                append_text(log_midi, f"Copied MIDI for '{song.title}' from {song.midi_abs_path}\n")
            except Exception:
                copy_error_count += 1
                append_text(log_midi, f"Warning: Failed to copy MIDI for '{song.title}' from {song.midi_abs_path}\n")

        if copy_error_count > 0:
            ui.warning_line(f"{txt_doc}: Failed to copy {copy_error_count} MIDI files")

        # Copy midi README, if set in config, into midi result dir
        readme_midi = cfg.mididir_readme_file
        if readme_midi:
            if readme_midi.exists():
                shutil.copy2(readme_midi, cur_res_midi / "README.md")
            else:
                append_text(log_midi, f"Warning: Readme for MIDI directories does not exist: {readme_midi}\n")
                ui.warning_line(f"{txt_doc}: Readme for MIDI dir does not exist: {readme_midi}")
        resultlist.append_line(RESULT_TYPE_MIDIDIR, cur_res_midi.name)
        step += 1

    # Audio encodes
    if do_audio:
        ui.exec_line(f"{txt_doc}: {ui.fmt_step(step)} encode audio (ulsbs-midi2audio)")
        cur_res_audio = result_dir / RESULT_AUDIO_SUBDIRNAME / processed_tex.stem
        safe_rm_tree(cur_res_audio)
        ensure_dir(cur_res_audio)
        log_audio = job.compile_dir / f"log-{step:02d}_encode-audio.log"

        for song in songs_with_midi:
            parent = cur_res_audio
            if song.chapter_slug:
                parent = parent / song.chapter_slug
            ensure_dir(parent)

            if song.number is not None:
                num_str = f"{song.number:03d}"
            else:
                num_str = f"{song.order_index:03d}"
            base = f"{num_str}__{song.title_slug}__from-midi"
            out_base = parent / base

            args = [
                "python3",
                "-m",
                "ulsbs.tools.midi2audio",
                "--force-overwrite",
                "--verbose",
                "--mp3-vbr-quality", "6",  # 0-9, lower is better
                "--mp3",
            ]
            # loudnorm (slow) / limiter (fast)
            if cfg.fast_audio_encode:
                args += [
                    "--enable-loudnorm",
                    "0",
                    "--enable-limiter",
                    "1"
                ]
            else:
                args += [
                    "--enable-loudnorm",
                    "1",
                    "--enable-limiter",
                    "0"
                ]
            # metadata tags
            if song.number:
                args += [
                    "--tag-tracknr",
                    str(song.number),
                ]
            if song.title:
                args += [
                    "--tag-tracktitle",
                    song.title,
                ]
            if song.options and song.options.get("by"):
                args += [
                    "--tag-trackartist",
                    song.options.get("by"),
                ]
            if song.chapter_title:
                args += [
                    "--tag-albumtitle",
                    song.chapter_title,
                ]
            args += [
                "--tag-albumartist",
                GENAUDIO_ALBUMTITLE,
                "--tag-image",
                str(job.compile_dir / _JOB_ULSBS_ASSETS_DIRNAME / "img" / "ulsbs-album-cover-for-generated-audio.png")
            ]
            # input and output file
            args += [
                "--outfile-basename",
                str(out_base),
                str(song.midi_abs_path),
            ]
            try:
                run_cmd(args, cwd=job.compile_dir, stdout_path=log_audio, stderr_to_stdout=True, check=True, append=True)
            except Exception:
                raise CompileError("ulsbs-midi2audio failed while encoding audio", log_audio)

        # Copy audio README, if set in config, into audio result dir
        readme_audio = cfg.audiodir_readme_file
        if readme_audio:
            if readme_audio.exists():
                shutil.copy2(readme_audio, cur_res_audio / "README.md")
            else:
                append_text(log_midi, f"Warning: Readme for audio directories does not exist: {readme_audio}\n")
                ui.warning_line(f"{txt_doc}: Readme for audio does not exist: {readme_audio}")
        resultlist.append_line(RESULT_TYPE_AUDIODIR, cur_res_audio.name)
        step += 1

    return step


def analyze_warnings(
    ui: UI,
    cfg: Config,
    job: Job,
    lilypond_log: Path,
    last_lualatex_log: Path
) -> int:
    """Count and summarize warnings from lilypond and LuaLaTeX logs."""
    txt_doc = ui.fmt_doc(f"{job.doc_stem}:{job.variant}", job.color)
    total_warn = 0
    lp_all_warn = 0
    tex_all_warn = 0
    try:
        # LilyPond warnings (skip for lyrics variant)
        if job.variant != "lyrics" and lilypond_log and lilypond_log.exists():
            lp_log_txt = read_text(lilypond_log)
            lp_all_warn = len(re.findall(r"warning", lp_log_txt, flags=re.I))
            lp_bar_warn = len(re.findall(r"warning: barcheck", lp_log_txt, flags=re.I))
            lp_auto_warn = len(re.findall(r"warning: Unable to auto-detect default settings", lp_log_txt, flags=re.I))
            if lp_all_warn > 0 and lp_auto_warn == 1:
                lp_all_warn -= 1
            if lp_all_warn:
                ui.warning_line(f"{txt_doc}: Lilypond warnings - all: {lp_all_warn} (barcheck: {lp_bar_warn})")
            total_warn += lp_all_warn
    except Exception:
        ui.warning_line(f"{txt_doc}: Lilypond warnings - failed to read the log file")

    try:
        # TeX warnings (from the last LuaLaTeX pass)
        if last_lualatex_log and last_lualatex_log.exists():
            lt_log_txt = read_text(last_lualatex_log)
            tex_all_warn = len(re.findall(r"warning", lt_log_txt, flags=re.I))
            tex_font_warn = len(re.findall(r"Font Warning", lt_log_txt, flags=re.I))
            if tex_all_warn:
                ui.warning_line(f"{txt_doc}: TeX warnings - all: {tex_all_warn} (font: {tex_font_warn})")
            if tex_font_warn > 20:
                ui.space_line(ui.colorize("Concerning amount of font warnings!", ui.C_RED))
            total_warn += tex_all_warn

    except Exception:
        ui.warning_line(f"{txt_doc}: TeX warnings - failed to read the log file")

    if total_warn > 0 and not cfg.clean_temp:
        if lp_all_warn:
            ui.see_line(TEMP_DIRNAME + '/' + str(lilypond_log.relative_to(lilypond_log.parent.parent.parent)))
        if tex_all_warn:
            ui.see_line(TEMP_DIRNAME + '/' + str(last_lualatex_log.relative_to(last_lualatex_log.parent.parent.parent)))

    return total_warn


def compile_one_job(
    ui: UI,
    assets: EngineAssets,
    cfg: Config,
    job: Job,
) -> int:
    """Compile a single job end-to-end, raising on failure.

    Returns the total number of warnings reported by analyze_warnings for this job.
    """
    txt_doc = ui.fmt_doc(f"{job.doc_stem}:{job.variant}", job.color)
    ui.start_line(txt_doc)

    lock = JobLock(job.compile_dir)
    lock.acquire()

    try:
        prepare_compile_dir(ui=ui, assets=assets, cfg=cfg, job=job)
        input_tex = make_variant_tex(job)
        env: dict[str, str]
        lp_include_args: list[str]
        env, lp_include_args = build_tool_include_paths(job=job)

        # Step counter for log numbering
        step = 1

        # 1) lilypond-book (+ overlay to job root)
        try:
            processed_tex, lp_log, step = run_lilypond_book(
                ui=ui,
                proj_content_dir=cfg.runtime.project_paths.content_dir,
                job=job,
                input_tex=input_tex,
                env=env,
                lp_include_args=lp_include_args,
                step=step,
            )
        except CompileError as ce:
            die_log(ui, cfg, job, cwd=job.compile_dir, message=str(ce), log_path=ce.log_path)

        basename = processed_tex.stem
        cwd = job.compile_dir
        result_dir = cfg.runtime.project_paths.result_dir
        ensure_dir(result_dir)

        # 2) lualatex pass 1 (draftmode)
        try:
            last_tex_log, step = run_lualatex_pass(ui, cfg, job, basename, env, step, pass_no=1, draftmode=True)
        except CompileError as ce:
            die_log(ui, cfg, job, cwd=cwd, message=str(ce), log_path=ce.log_path)

        # 3) indices (if not selection)
        if not basename.startswith(SELECTION_FNAME_PREFIX):
            try:
                step = run_texlua_indices(ui, cfg, job, basename, env, step)
            except CompileError as ce:
                die_log(ui, cfg, job, cwd=cwd, message=str(ce), log_path=ce.log_path)

        # 4) lualatex pass 2 (draftmode)
        try:
            last_tex_log, step = run_lualatex_pass(ui, cfg, job, basename, env, step, pass_no=2, draftmode=True)
        except CompileError as ce:
            die_log(ui, cfg, job, cwd=cwd, message=str(ce), log_path=ce.log_path)

        # 5) lualatex pass 3
        try:
            last_tex_log, step = run_lualatex_pass(ui, cfg, job, basename, env, step, pass_no=3, draftmode=False)
        except CompileError as ce:
            die_log(ui, cfg, job, cwd=cwd, message=str(ce), log_path=ce.log_path)

        # Ensure PDF exists and copy to result dir
        produced_pdf = cwd / f"{basename}.pdf"
        if not produced_pdf.exists():
            die_log(ui, cfg, job, cwd=cwd, message="Expected PDF not produced by lualatex.", log_path=last_tex_log)
        dst_pdf = result_dir / produced_pdf.name
        shutil.copy2(produced_pdf, dst_pdf)
        resultlist.append_line(RESULT_TYPE_MAIN_PDF, produced_pdf.name)

        # 6) Optional printouts
        try:
            step = run_context_printouts(ui, cfg, job, basename, env, step)
        except CompileError as ce:
            die_log(ui, cfg, job, cwd=cwd, message=str(ce), log_path=ce.log_path)

        # 7) Optional cover image extraction
        try:
            step = run_coverimage_extraction(ui, cfg, job, basename, env, step)
        except CompileError as ce:
            die_log(ui, cfg, job, cwd=cwd, message=str(ce), log_path=ce.log_path)

        # 8) Build song database
        try:
            song_db, step = build_song_db(ui=ui, cfg=cfg, job=job, processed_tex=processed_tex, step=step)
        except CompileError as ce:
            die_log(ui, cfg, job, cwd=cwd, message=str(ce), log_path=ce.log_path)

        # 9) MIDI/audio assets
        try:
            step = run_midi_audio(ui=ui, assets=assets, cfg=cfg, job=job, processed_tex=processed_tex, db=song_db, step=step)
        except CompileError as ce:
            die_log(ui, cfg, job, cwd=cwd, message=str(ce), log_path=ce.log_path)

        # Analyze warnings using lilypond log and the last lualatex log
        warn_count = analyze_warnings(ui, cfg, job, lilypond_log=lp_log, last_lualatex_log=last_tex_log)

        ui.success_line(f"{ui.fmt_doc(str(dst_pdf.name), job.color)}: Compilation successful!")
        return warn_count
    finally:
        lock.release()


def run_jobs_parallel(
    ui: UI,
    jobs: List[Job],
    assets: EngineAssets,
    cfg: Config,
) -> ParallelRunResult:
    """Run jobs in parallel threads and collect structured results.

    Returns ParallelRunResult with named successes and failures, plus total warnings.
    """
    successes: List[JobSuccess] = []
    failures: List[JobFailure] = []
    stop_requested = {"value": False}

    def handle_sigint(signum, frame):
        ABORT_EVENT.set()
        stop_requested["value"] = True
        # Don't raise here; let the main loop notice and cancel futures.

    old_int = signal.signal(signal.SIGINT, handle_sigint)

    ABORT_EVENT.clear()

    try:
        with cf.ThreadPoolExecutor(max_workers=cfg.max_parallel) as ex:
            fut_map = {}

            # Submit all jobs up front (simple) – cancellation will stop those not started yet.
            for job in jobs:
                fut = ex.submit(
                    compile_one_job,
                    ui, assets, cfg,
                    job,
                )
                fut_map[fut] = job

            # Collect results
            for fut in cf.as_completed(fut_map):
                if stop_requested["value"]:
                    # Cancel anything still pending
                    for f in fut_map:
                        f.cancel()
                    break

                job = fut_map[fut]
                try:
                    warn_count = fut.result()
                    successes.append(JobSuccess(job=job, warning_count=warn_count))
                except KeyboardInterrupt:
                    stop_requested["value"] = True
                    for f in fut_map:
                        f.cancel()
                    break
                except Exception as e:
                    if ABORT_EVENT.is_set():
                        # Ignore errors that occur during abort cascade
                        continue
                    failures.append(JobFailure(job=job, reason=str(e)))

            if stop_requested["value"]:
                # Let executor shut down; any running jobs may finish, but we will exit politely.
                raise KeyboardInterrupt()

    finally:
        signal.signal(signal.SIGINT, old_int)

    return ParallelRunResult(
        successes=successes,
        failures=failures,
        total_warnings=sum(s.warning_count for s in successes),
    )
