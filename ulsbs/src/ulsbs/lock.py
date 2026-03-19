# SPDX-FileCopyrightText: 2016-2026 Lari Natri <lari.natri@iki.fi>
# SPDX-License-Identifier: GPL-3.0-or-later

"""
Simple file-based per-job lock handling for temp directories.
This file is part of the 'ulsbs' package.
"""

from __future__ import annotations

import fcntl  # Linux/Unix
import os
import time

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List

from .util import ensure_dir

LOCK_FILENAME = ".ulsbs.lock"


@dataclass
class JobLock:
    """Non-blocking exclusive lock within a job's compile directory."""

    lock_path: Path
    _fd: int | None = None

    def acquire(self) -> None:
        """Acquire the job lock or raise if already held by another process."""
        ensure_dir(self.lock_path)

        # Open/create lock file
        fd = os.open(str(self.lock_path / LOCK_FILENAME), os.O_RDWR | os.O_CREAT, 0o666)

        try:
            # Non-blocking exclusive lock
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            os.close(fd)
            raise RuntimeError("Locked (another process is compiling this job)") from None

        # We own the lock now; write some human-readable info (optional)
        try:
            os.ftruncate(fd, 0)
            info = f"pid={os.getpid()}\nstarted={int(time.time())}\n"
            os.write(fd, info.encode("utf-8"))
            os.fsync(fd)
        except Exception:
            pass

        self._fd = fd

    def release(self) -> None:
        """Release the job lock if held."""
        if self._fd is None:
            return
        try:
            fcntl.flock(self._fd, fcntl.LOCK_UN)
        except Exception:
            pass
        try:
            os.close(self._fd)
        except Exception:
            pass
        self._fd = None


def find_lock_files(temp_root: Path, max_depth: int = 0) -> List[Path]:
    """
    Find lock files under temp_root.

    max_depth:
      <= 0 -> unlimited depth (recursive)
      >  0 -> only that many levels below temp_root

    Depth is counted by dirs:
      1 -> temp_root/*/
      2 -> temp_root/*/*/
    """
    if not temp_root.exists():
        return []
    results: List[Path] = []
    # Unlimited depth -> use rglob
    if max_depth <= 0:
        for p in temp_root.rglob(LOCK_FILENAME):
            if p.is_file():
                results.append(p)
        return results
    # Depth-limited search
    current_level = [temp_root]
    for _ in range(max_depth):
        next_level = []
        for base in current_level:
            try:
                for child in base.iterdir():
                    if not child.is_dir():
                        continue
                    next_level.append(child)

                    lock_file = child / LOCK_FILENAME
                    if lock_file.is_file():
                        results.append(lock_file)
            except Exception:
                continue
        current_level = next_level
        if not current_level:
            break
    return results


def alive_locks(lock_files: Iterable[Path]) -> List[Path]:
    """Return the subset of lock files that are currently held by others."""
    alive: List[Path] = []
    for lf in lock_files:
        if lf.exists():
            fd = os.open(str(lf), os.O_RDWR | os.O_CREAT, 0o666)
            try:
                try:
                    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    # acquired -> not held; release
                    fcntl.flock(fd, fcntl.LOCK_UN)
                except BlockingIOError:
                    # lock is held by another
                    alive.append(lf)
            finally:
                os.close(fd)
    return alive
