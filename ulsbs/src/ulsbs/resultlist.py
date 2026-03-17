# SPDX-FileCopyrightText: 2016-2026 Lari Natri <lari.natri@iki.fi>
# SPDX-License-Identifier: GPL-3.0-or-later

"""
Maintain a text file listing compilation results for deploy steps.
This file is part of the 'ulsbs' package.
"""

from __future__ import annotations

from pathlib import Path

from .constants import (
    RESULTLIST_SEPARATOR,
    RESULT_TYPE_INFO,
    RESULTLIST_BASENAME,
)
from .pipeline import ParallelRunResult
from .util import ensure_dir, read_text, create_unique_id, current_time_human_readable

# Module-level variables, all initialized by initialize()
_initialized: bool = False
_unique_id: str | None = None
_dir: Path | None = None
_resultlist_file: Path | None = None  # with path
_resultlist_filename: Path | None = None
_finalized: bool = False
_moved: bool = False


def initialize(directory: Path, unique_id: str = "") -> None:
    """Initialize the result list under 'directory'."""

    global _initialized, _dir, _unique_id
    global _resultlist_file, _resultlist_filename

    _dir = directory
    if unique_id is None or unique_id == "":
        _unique_id = create_unique_id()
    else:
        _unique_id = unique_id

    _resultlist_filename = f"{RESULTLIST_BASENAME}_{_unique_id}.txt"
    _resultlist_file = (_dir / _resultlist_filename).resolve()
    _initialized = True


def initialize_with_file(reslist_file: Path) -> None:
    """Initialize using an existing result list file path."""

    global _initialized, _unique_id, _dir
    global _resultlist_file, _resultlist_filename
    global _finalized, _moved

    if not reslist_file.name.startswith(RESULTLIST_BASENAME):
        raise Exception(f"Result list file candidate is incorrecly named: {reslist_file}")

    if not (reslist_file.exists() and reslist_file.is_file()):
        raise Exception(f"Result list file candidate does not exist or is not a file: {reslist_file}")

    _resultlist_file = reslist_file.resolve()
    _dir = _resultlist_file.parent
    _resultlist_filename = reslist_file.name
    _initialized = True
    _finalized = False
    _moved = False


def unique_id() -> str:
    """Return the unique ID for this run."""

    if not _initialized:
        raise RuntimeError("resultlist not initialized. Call initialize() first.")

    return _unique_id


def exists() -> bool:
    """Return True if the current result list file exists."""
    if not _initialized:
        raise RuntimeError("resultlist not initialized. Call initialize() first.")

    return _resultlist_file.exists()


def lines() -> list[str]:
    """Return all lines from the result list file."""
    if not _initialized:
        raise RuntimeError("resultlist not initialized. Call initialize() first.")

    return read_text(_resultlist_file).splitlines()


def append_line(rtype: str, name: str) -> None:
    """Append a result line to the result file."""

    if not _initialized:
        raise RuntimeError("resultlist not initialized. Call initialize() first.")

    with _resultlist_file.open("a", encoding="utf-8") as f:
        f.write(f"{rtype}{RESULTLIST_SEPARATOR}{name}\n")


def append_line_if_missing(rtype, name) -> None:
    """Append the line if it is not already present."""
    if not _initialized:
        raise RuntimeError("resultlist not initialized. Call initialize() first.")

    data = read_text(_resultlist_file) if exists() else ""
    line = f"{rtype}{RESULTLIST_SEPARATOR}{name}"
    if line not in data:
        append_line(rtype, name)


def write_header(remove_existing_file: bool = True) -> None:
    """Write the compilation header to the result file."""

    if not _initialized:
        raise RuntimeError("resultlist not initialized. Call initialize() first.")

    if remove_existing_file and _resultlist_file.exists():
        _resultlist_file.unlink()

    started = current_time_human_readable()
    append_line(RESULT_TYPE_INFO, f"Compilation started at: {started}")


def finalize(
    dst_dir: Path | None = None,
    runresult: ParallelRunResult | None = None,
    delete_existing_resultlists_in_dst: bool = False
) -> None:
    """
    Finalize the list and optionally copy it to dst_dir, deleting old ones.
    """

    global _finalized
    global _moved

    if not _initialized:
        raise RuntimeError("resultlist not initialized. Call initialize() first.")

    if runresult:
        append_line(RESULT_TYPE_INFO, f"Jobs succeeded: {len(runresult.successes)} (with {runresult.total_warnings} warnings)")
        append_line(RESULT_TYPE_INFO, f"Jobs failed: {len(runresult.failures)}")

    ended = current_time_human_readable()
    append_line(RESULT_TYPE_INFO, f"Compilation ended at: {ended}")
    _finalized = True

    if dst_dir is not None:
        ensure_dir(dst_dir)
        if delete_existing_resultlists_in_dst:
            for file in resultfiles_in_dir(dst_dir):
                file.unlink()
        (dst_dir / _resultlist_filename).write_text(
            _resultlist_file.read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        initialize(dst_dir, _unique_id)
        _moved = True


def abort(dst_dir: Path | None = None) -> None:
    """Write the compilation abort message to the result file."""

    global _finalized, _moved

    if not _initialized:
        raise RuntimeError("resultlist not initialized. Call initialize() first.")

    ended = current_time_human_readable()
    append_line(RESULT_TYPE_INFO, f"Compilation ABORTED at: {ended}")
    _finalized = True

    if dst_dir is not None:
        ensure_dir(dst_dir)
        (dst_dir / _resultlist_filename).write_text(
            _resultlist_file.read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        initialize(dst_dir, _unique_id)
        _moved = True


def delete():
    """Delete the result list file and reset internal state."""

    global _initialized, _unique_id, _dir
    global _resultlist_file, _resultlist_filename
    global _finalized, _moved

    if not _initialized:
        raise RuntimeError("resultlist not initialized. Call initialize() first.")


    if _resultlist_file.exists() and _resultlist_file.is_file():
        _resultlist_file.unlink()

    _initialized = False
    _unique_id = None
    _dir = None
    _resultlist_file = None
    _resultlist_filename = None
    _finalized = False
    _moved = False


def resultfiles_in_dir(dir_path: Path) -> list[Path]:
    """Return all result list files in dir_path (non-recursive)."""

    if not dir_path.exists() or not dir_path.is_dir():
        return []

    pattern = f"{RESULTLIST_BASENAME}_*.txt"
    return [p for p in dir_path.glob(pattern) if p.is_file()]
