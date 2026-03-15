# SPDX-FileCopyrightText: 2016-2026 Lari Natri <lari.natri@iki.fi>
# SPDX-License-Identifier: GPL-3.0-or-later

"""
Prepare and manage the temp directory used for compiles.
This file is part of the 'ulsbs' package.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Tuple

from .config import Config
from .lock import find_lock_files, alive_locks
from .ui import UI
from .util import ensure_dir, safe_rm_tree, read_text, symlink_unsupported


@dataclass(frozen=True)
class TempState:
    """Describe project temp path, effective root, and link state."""
    project_temp_path: Path          # <project>/temp
    effective_temp_root: Path        # resolved target where jobs are actually stored
    is_symlink: bool

def _desired_effective_temp_root(project_temp_dir: Path, use_system_tmp: bool) -> Path:
    """Return desired effective temp root based on config flag."""
    if use_system_tmp:
        user = os.environ.get("USER") or os.environ.get("USERNAME") or "user"
        return (Path("/tmp") / f"ulsbs_{user}").resolve()
    # project-local temp root
    return project_temp_dir.resolve()

def _current_temp_state(project_temp_dir: Path) -> TempState:
    """Return current TempState for the project's temp directory."""
    if project_temp_dir.is_symlink():
        try:
            return TempState(project_temp_dir, project_temp_dir.resolve(), True)
        except Exception:
            # broken symlink
            return TempState(project_temp_dir, project_temp_dir, True)
    return TempState(project_temp_dir, project_temp_dir, False)

def _clear_temp_root(temp_root: Path) -> bool:
    """Clear all children under temp_root. Return True if it existed."""
    if not temp_root.exists():
        return False
    for child in temp_root.iterdir():
        safe_rm_tree(child)
    return True

def setup_temp_dir(ui: UI, cfg: Config) -> None:
    """
    Prepare <project>/temp safely.

    Rules:
      - If live locks exist under current effective root, do not clear it.
      - If switching roots while locks exist, abort the run.
      - If no live locks exist, adjust root and clear it for a clean run.
    """
    project_temp_dir = cfg.runtime.project_paths.temp_dir
    use_system_tmp = cfg.use_system_tmp
    desired_root = _desired_effective_temp_root(project_temp_dir, use_system_tmp)
    current = _current_temp_state(project_temp_dir)
    current_root = current.effective_temp_root

    # Ensure desired root exists (especially system tmp path)
    ensure_dir(desired_root)

    # Check existing temp root for live locks BEFORE touching anything
    lock_files = find_lock_files(current_root, 2)
    alive = alive_locks(lock_files)

    if alive:
        # If the user is trying to switch temp root while compiles are running, abort.
        if desired_root.resolve() != current_root.resolve():
            sample = alive[0]
            ui.error_line("Other compile process is active.")
            ui.space_line(f"Active lock: {sample}")
            ui.space_line(f"Current temp root: {current_root}")
            ui.space_line(f"Requested temp root: {desired_root}")
            raise SystemExit("Other compile process is using different temp location.")
        # Same temp root: do NOT clear. Let per-job locks handle contention.
        ui.debug_line(f"Temp in use; preserving: {current_root}")
        return

    # No live locks -> safe to (re)point and clear
    if use_system_tmp:
        # ensure <project>/temp is a symlink to desired_root
        if project_temp_dir.exists() or project_temp_dir.is_symlink():
            safe_rm_tree(project_temp_dir)
        try:
            project_temp_dir.symlink_to(desired_root, target_is_directory=True)
            # clear actual temp root, unless going for interactive shell
            if not cfg.shell:
                _clear_temp_root(desired_root)
            ui.debug_line(f"Using system temp: {desired_root}")
            return
        except (OSError, NotImplementedError) as e:
            # Filesystem may not support symlinks (e.g. some network shares or
            # FAT volumes).Fall back to using a project-local temp directory
            # instead.
            if not symlink_unsupported(e):
                raise
            ui.warning_line("Symlinks are not supported for the project temp dir;")
            ui.space_line("falling back to project-local 'temp' directory.")

    # ensure <project>/temp is a real directory
    if project_temp_dir.is_symlink():
        project_temp_dir.unlink()
    ensure_dir(project_temp_dir)
    # clear actual temp root, unless going for interactive shell
    if not cfg.shell:
        _clear_temp_root(project_temp_dir)
    ui.debug_line(f"Using project temp: {project_temp_dir}")

def clear_temp_dir_if_no_locks(project_temp_dir: Path) -> bool:
    """Clear project temp dir if no live locks remain. Return True if done."""
    # Check existing temp root for live locks before touching anything
    if not project_temp_dir.exists():
        return False
    lock_files = find_lock_files(project_temp_dir, 2)
    alive = alive_locks(lock_files)
    if not alive:
        return _clear_temp_root(project_temp_dir)
    else:
        return False
