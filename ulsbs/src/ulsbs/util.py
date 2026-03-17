# SPDX-FileCopyrightText: 2016-2026 Lari Natri <lari.natri@iki.fi>
# SPDX-License-Identifier: GPL-3.0-or-later

"""
Small utility helpers: filesystem ops, subprocess, hashing, quoting.
This file is part of the 'ulsbs' package.
"""

from __future__ import annotations

import errno
import hashlib
import time
import os
import re
import shlex
import shutil
import subprocess
from pathlib import Path
from typing import Dict, List
from uuid import uuid4


def create_unique_id(include_time: bool = True) -> str:
    """Create a short unique ID, optionally prefixed with a timestamp."""
    result = ""
    if include_time:
        result = time.strftime("%Y-%m-%dT%H.%M.%S%z")
    result += f"_{str(uuid4())[:8]}"
    return result


def current_time_human_readable() -> str:
    """Return current time as 'YYYY-MM-DD HH:MM:SS ±TZ'."""
    return time.strftime("%Y-%m-%d %H:%M:%S %z")


def which(cmd: str) -> str | None:
    """Return full path to cmd in PATH, or None if not found."""
    return shutil.which(cmd)


def safe_rm_tree(p: Path) -> None:
    """
    Safely remove a filesystem path.

    - No-op if the path does not exist.
    - Unlinks files and symlinks (does not follow symlinks).
    - Recursively deletes real directories.
    """
    # Nothing to do if the path is missing
    if not p.exists():
        return
    # Unlink files and symlinks to avoid following links
    if p.is_symlink() or p.is_file():
        p.unlink()
        return
    # Recursively remove a real directory tree
    shutil.rmtree(p)


def ensure_dir(p: Path) -> None:
    """
    Ensure that directory 'p' exists.

    Creates the directory and any missing parent directories. This is safe to
    call repeatedly; if the directory already exists, no error is raised.
    Raises FileExistsError if a non-directory object exists at 'p'.
    """
    p.mkdir(parents=True, exist_ok=True)


def symlink_unsupported(exc: BaseException) -> bool:
    """Return True if *exc* indicates that symlinks are not supported here.

    This detects common errno values for filesystems or platforms that do not
    support symlinks (or where creating them is not permitted).
    """
    if isinstance(exc, NotImplementedError):
        return True
    if isinstance(exc, OSError):
        unsupported_errnos = {errno.EPERM}
        eop = getattr(errno, "EOPNOTSUPP", None)
        if eop is not None:
            unsupported_errnos.add(eop)
        enosys = getattr(errno, "ENOSYS", None)
        if enosys is not None:
            unsupported_errnos.add(enosys)
        return exc.errno in unsupported_errnos
    return False


def ensure_symlink(dst: Path, target: Path, force_dir: bool = False, fallback_copy: bool = True) -> None:
    """
    Ensure that 'dst' is a symlink pointing to 'target' (file or directory).

    If creating a symlink is not possible on this filesystem (for example on
    some network shares or FAT volumes) and fallback_copy is True, a real copy
    of the target is created instead of failing.

    Behavior:
      - If a path already exists at 'dst' (file, directory, or symlink), it is removed.
        Directories are removed recursively via safe_rm_tree. This also handles broken
        symlinks (dst.is_symlink() may be True while dst.exists() is False).
      - The parent directory of 'dst' is created if missing.
      - A symlink is created from 'dst' to 'target'.

    Notes:
      - On Windows, the target_is_directory hint must be correct when creating symlinks.
        We set it to True only if:
          * force_dir is True, or
          * target exists and is a directory.
        Otherwise, we assume the target is a file (even if it does not exist).
      - On POSIX systems, target_is_directory is ignored by pathlib.

    Parameters:
      dst: Destination path for the symlink to create.
      target: Path to which the symlink should point.
      force_dir: If True, treat target as a directory when creating the symlink.
      fallback_copy: If True, fall back to copying the target if symlinks are
        not supported or not permitted.
    """
    # 1) Remove any existing entry at dst (file, directory, or symlink, including broken links)
    if dst.exists() or dst.is_symlink():
        safe_rm_tree(dst)

    # 2) Ensure the destination's parent directory exists
    dst.parent.mkdir(parents=True, exist_ok=True)

    # 3) Determine directory hint for Windows; ignored on POSIX
    is_dir_hint = force_dir or (target.exists() and target.is_dir())

    # 4) Create the symlink, with optional copy fallback
    try:
        dst.symlink_to(target, target_is_directory=is_dir_hint)
        return
    except (OSError, NotImplementedError) as e:
        if not (fallback_copy and symlink_unsupported(e)):
            raise
        last_error = e

    # Fallback path: copy the target instead of creating a symlink.
    target_is_dir = is_dir_hint or (target.exists() and target.is_dir())
    if target.exists() and target_is_dir:
        shutil.copytree(target, dst, dirs_exist_ok=True)
    elif target.exists() and target.is_file():
        shutil.copy2(target, dst)
    else:
        # Target does not exist; cannot sensibly copy. Re-raise original error.
        raise last_error


def symlink_tree(src_root: Path, dst_root: Path, fallback_copy: bool = True) -> None:
    """
    Replicate the directory hierarchy of src_root into dst_root and create
    a symlink for every non-directory entry found under src_root.

    - Directories are created as real directories in dst_root.
    - Files become symlinks pointing to the *absolute* source path.
    - Symlinks in src_root are reproduced as symlinks (same target text)
      if possible; if that fails, we fall back to linking to the resolved
      real file.

    Safety:
    - Never deletes dst_root directories wholesale.
    - Replaces dst_root files/symlinks if src has an entry at that path.
    - If src has a file/symlink where dst has a real directory, raises (conflict),
      because deleting a directory could lose resources.

    Parameters:
      src_root: Source tree to mirror.
      dst_root: Destination tree root.
      fallback_copy: If True, when creating a symlink fails because symlinks
        are unsupported, copy the source entry instead of raising.
    """
    src_root = src_root.resolve()
    dst_root = dst_root.resolve()

    if not src_root.exists():
        return

    for src in src_root.rglob("*"):
        rel = src.relative_to(src_root)
        dst = dst_root / rel

        if src.is_dir() and not src.is_symlink():
            dst.mkdir(parents=True, exist_ok=True)
            continue

        # src is file or symlink-to-file/dir; dst must not be a real directory
        if dst.exists() and dst.is_dir() and not dst.is_symlink():
            raise RuntimeError(f"symlink_tree conflict: destination is a directory but source is a file/link: {dst}")

        dst.parent.mkdir(parents=True, exist_ok=True)

        # Replace existing file/symlink at dst
        if dst.exists() or dst.is_symlink():
            if dst.is_symlink() or dst.is_file():
                dst.unlink(missing_ok=True)
            elif dst.is_dir():
                # should have been caught above, but keep as guard
                raise RuntimeError(f"symlink_tree conflict: cannot overwrite directory: {dst}")

        if src.is_symlink():
            # replicate symlink target (best-effort)
            try:
                target = src.readlink()
                try:
                    dst.symlink_to(target, target_is_directory=src.is_dir())
                except (OSError, NotImplementedError) as e:
                    if not (fallback_copy and symlink_unsupported(e)):
                        raise
                    # Fallback: copy the resolved target instead of creating a symlink.
                    resolved = src.resolve()
                    if resolved.is_dir():
                        shutil.copytree(resolved, dst, dirs_exist_ok=True)
                    else:
                        shutil.copy2(resolved, dst)
            except Exception:
                # fall back to linking to resolved path, or copying if symlinks unsupported
                resolved = src.resolve()
                try:
                    dst.symlink_to(resolved, target_is_directory=resolved.is_dir())
                except (OSError, NotImplementedError) as e:
                    if not (fallback_copy and symlink_unsupported(e)):
                        raise
                    if resolved.is_dir():
                        shutil.copytree(resolved, dst, dirs_exist_ok=True)
                    else:
                        shutil.copy2(resolved, dst)
        else:
            # link to absolute path for robustness (cwd doesn't matter)
            try:
                dst.symlink_to(src, target_is_directory=False)
            except (OSError, NotImplementedError) as e:
                if not (fallback_copy and symlink_unsupported(e)):
                    raise
                shutil.copy2(src, dst)


def overlay_tree(src_root: Path, dst_root: Path, move: bool = False) -> None:
    """
    Overlay-copy (or overlay-move) everything from src_root into dst_root.

    Semantics:
      - Only paths that exist under src_root are applied to dst_root.
      - Directories in dst_root are never "replaced" wholesale; they are created if missing.
        (This avoids clobbering existing dirs that may contain extra resources.)
      - Files/symlinks in dst_root are replaced if src_root provides a file/symlink at that path.
      - If src_root provides a directory at a path where dst_root currently has a file/symlink,
        that file/symlink is removed so a directory can be created.
      - If src_root provides a file/symlink at a path where dst_root currently has a directory,
        this is considered a conflict; the directory is NOT removed automatically (to avoid data loss).
        An exception is raised, because the overlay cannot be applied safely.

    Symlinks:
      - If src path is a symlink, we recreate a symlink at destination (same link target),
        replacing any existing dst file/symlink. If dst is a directory, that's a conflict.

    move=True:
      - For regular files, attempts atomic rename/replace using os.replace().
      - If that fails due to cross-device move (EXDEV), falls back to copy2+unlink.
      - For symlinks, creates dest symlink then removes src symlink.
      - After moving, empty directories under src_root are removed (best-effort).

    Note:
      - This function does NOT remove files from dst_root that do not exist in src_root.
      - It also does not try to replicate permissions/ownership beyond shutil.copy2 defaults.
    """
    src_root = src_root.resolve()
    dst_root = dst_root.resolve()

    if not src_root.exists():
        return

    # Process deeper paths first so file-vs-dir conflicts are handled deterministically.
    # (rglob order isn't guaranteed; we'll sort by path depth and lexicographically.)
    all_paths = list(src_root.rglob("*"))
    all_paths.sort(key=lambda p: (-len(p.relative_to(src_root).parts), str(p)))

    def _rm_dst_file_or_link(p: Path) -> None:
        # Remove only files/links; if directory, leave for caller to decide.
        if p.is_symlink() or p.is_file():
            p.unlink(missing_ok=True)

    def _ensure_dir(p: Path) -> None:
        p.mkdir(parents=True, exist_ok=True)

    def _copy_file(src: Path, dst: Path) -> None:
        _ensure_dir(dst.parent)
        # Replace destination if it's a file/link
        if dst.is_symlink() or dst.is_file():
            dst.unlink(missing_ok=True)
        # If destination is a directory, that's a conflict (see semantics above)
        if dst.exists() and dst.is_dir():
            raise RuntimeError(f"overlay_tree conflict: cannot overwrite directory with file: {dst}")
        shutil.copy2(src, dst)

    def _move_file(src: Path, dst: Path) -> None:
        _ensure_dir(dst.parent)
        # If dst is dir, conflict
        if dst.exists() and dst.is_dir():
            raise RuntimeError(f"overlay_tree conflict: cannot overwrite directory with file: {dst}")

        # Ensure dst isn't a file/link (os.replace handles it, but ensure no symlink-to-dir weirdness)
        if dst.is_symlink() or dst.is_file():
            dst.unlink(missing_ok=True)

        try:
            os.replace(src, dst)  # atomic if same filesystem; replaces existing file
        except OSError as e:
            if e.errno == errno.EXDEV:
                # cross-device move: copy then unlink
                shutil.copy2(src, dst)
                src.unlink(missing_ok=True)
            else:
                raise

    def _copy_symlink(src: Path, dst: Path) -> None:
        _ensure_dir(dst.parent)
        if dst.exists() or dst.is_symlink():
            # if dst is directory, conflict
            if dst.exists() and dst.is_dir() and not dst.is_symlink():
                raise RuntimeError(f"overlay_tree conflict: cannot overwrite directory with symlink: {dst}")
            _rm_dst_file_or_link(dst)
        target = src.readlink()
        try:
            dst.symlink_to(target)
        except (OSError, NotImplementedError) as e:
            if not symlink_unsupported(e):
                raise
            # Fallback: copy the resolved target instead of creating a symlink.
            resolved = src.resolve()
            if resolved.is_dir():
                shutil.copytree(resolved, dst, dirs_exist_ok=True)
            else:
                shutil.copy2(resolved, dst)

    def _move_symlink(src: Path, dst: Path) -> None:
        _copy_symlink(src, dst)
        src.unlink(missing_ok=True)

    # Apply overlay
    for src in all_paths:
        rel = src.relative_to(src_root)
        dst = dst_root / rel

        if src.is_dir() and not src.is_symlink():
            # If dst exists as file/link, remove it so directory can be created.
            if dst.is_symlink() or dst.is_file():
                _rm_dst_file_or_link(dst)
            _ensure_dir(dst)
            continue

        # src is file or symlink
        # If dst is a directory, we refuse to overwrite it (avoid deleting resources)
        if dst.exists() and dst.is_dir() and not dst.is_symlink():
            raise RuntimeError(f"overlay_tree conflict: destination is a directory but source is a file/link: {dst}")

        if src.is_symlink():
            if move:
                _move_symlink(src, dst)
            else:
                _copy_symlink(src, dst)
        else:
            if move:
                _move_file(src, dst)
            else:
                _copy_file(src, dst)

    # If move=True, try to remove now-empty dirs in src_root so caller can delete src_root.
    if move:
        # Walk directories from deepest to shallowest
        dirs = [p for p in src_root.rglob("*") if p.is_dir() and not p.is_symlink()]
        dirs.sort(key=lambda p: (-len(p.relative_to(src_root).parts), str(p)))
        for d in dirs:
            try:
                d.rmdir()  # only removes if empty
            except OSError:
                pass


def sync_tree(src_root: Path, dst_root: Path) -> int:
    """Synchronize a directory tree from *src_root* into *dst_root*.

    Semantics:
      - *dst_root* itself is never removed, only its contents.
      - Every file or directory that exists in *src_root* will exist at the
        same relative path under *dst_root* after the operation.
      - Files are copied only when they are new or their contents differ
        (as determined by :func:`files_are_identical`).
      - Files/directories that exist in *dst_root* but not in *src_root* are
        removed. Removals are symlink-aware: a symlink is unlinked without
        touching its target.

    Returns:
      The number of destination files that were left untouched because they
      were already identical to their source counterparts.
    """
    src_root = src_root.resolve()
    dst_root = dst_root.resolve()

    if not src_root.exists() or not src_root.is_dir():
        return 0

    # Ensure dst_root is a real directory; if something else is there, remove it.
    if dst_root.exists() and not dst_root.is_dir():
        # Only remove the path entry itself; if it is a symlink, do not touch its target.
        safe_rm_tree(dst_root)
    dst_root.mkdir(parents=True, exist_ok=True)

    skipped = 0
    seen_rel_paths: set[Path] = set()

    # First pass: create/update everything present in src_root.
    for src in src_root.rglob("*"):
        rel = src.relative_to(src_root)
        dst = dst_root / rel
        seen_rel_paths.add(rel)

        if src.is_dir() and not src.is_symlink():
            # Make sure the destination is a directory.
            if dst.exists() and (dst.is_file() or dst.is_symlink()):
                safe_rm_tree(dst)
            dst.mkdir(parents=True, exist_ok=True)
            continue

        # src is a file or a symlink
        # If dst is a real directory here, remove it so the file/symlink can be placed.
        if dst.exists() and dst.is_dir() and not dst.is_symlink():
            safe_rm_tree(dst)

        if dst.exists():
            # If both are regular files, check for identical contents.
            try:
                if src.is_file() and dst.is_file() and files_are_identical(src, dst):
                    skipped += 1
                    continue
            except Exception:
                # On any error, fall back to overwriting below.
                pass
            # Replace existing file/symlink with new content.
            safe_rm_tree(dst)

        dst.parent.mkdir(parents=True, exist_ok=True)

        if src.is_symlink():
            # Copy the resolved target contents; this mirrors shutil.copytree's
            # default behaviour of following symlinks for files.
            try:
                target = src.resolve(strict=True)
            except FileNotFoundError:
                # Broken symlink: best-effort copy of the link entry itself.
                shutil.copy2(src, dst)
            else:
                if target.is_dir():
                    shutil.copytree(target, dst, dirs_exist_ok=True)
                else:
                    shutil.copy2(target, dst)
        elif src.is_dir():
            # Defensive fallback; normally handled by the directory branch above.
            shutil.copytree(src, dst, dirs_exist_ok=True)
        else:
            shutil.copy2(src, dst)

    # Second pass: remove anything in dst_root that no longer exists in src_root.
    # Walk deepest paths first so that children are removed before parents.
    all_dst_paths = list(dst_root.rglob("*"))
    all_dst_paths.sort(key=lambda p: (-len(p.relative_to(dst_root).parts), str(p)))

    for dst in all_dst_paths:
        rel = dst.relative_to(dst_root)
        if rel in seen_rel_paths:
            continue
        # Path does not exist in source; remove it.
        safe_rm_tree(dst)

    return skipped


def regex_documentclass_ulsbs_songbook() -> re.Pattern[str]:
    r"""
    Matches a LaTeX \documentclass whose class starts with 'ulsbs-songbook',
    allowing optional [options], whitespace, newlines, and % EOL comments,
    but not when the line is commented out.
    """
    return re.compile(
        r"""
        ^[^\S\n]*(?!%)\\documentclass          # start of line; not commented
        (?:\s|%[^\n]*)*                        # whitespace or comments
        (?:                                    # optional [options]
            \[
                [^\]]*                         # anything except closing ]
            \]
            (?:\s|%[^\n]*)*                    # whitespace or comments
        )?
        \{
            (?:\s|%[^\n]*)*                    # whitespace or comments inside {
            ulsbs\-songbook[^\s\}%]*           # class name prefix with any suffix
            (?:\s|%[^\n]*)*                    # whitespace or comments before }
        \}
        """,
        re.VERBOSE | re.MULTILINE,
    )


def read_text(p: Path) -> str:
    """
    Read a text file as UTF-8, replacing undecodable bytes.

    Returns:
      The file contents as a string.
    """
    return p.read_text(encoding="utf-8", errors="replace")


def write_text(p: Path, data: str) -> None:
    """Write UTF-8 text to a file, creating parent directories if needed."""
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(data, encoding="utf-8")

def append_text(p: Path, data: str) -> None:
    """Append UTF-8 text to a file, creating parent directories if needed."""
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as f:
        f.write(data)


def blake2b_file(p: Path) -> str:
    """Compute the BLAKE2 hex digest of a file, streaming in 1 MiB chunks."""
    h = hashlib.sha256()
    with p.open("rb") as f:
        # Read and hash in fixed-size chunks to avoid large memory usage
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def files_are_identical(p1: Path, p2: Path) -> bool:
    """Check if two files have identical contents."""
    return p1.stat().st_size == p2.stat().st_size and blake2b_file(p1) == blake2b_file(p2)

def run_cmd(
    args: List[str],
    cwd: Path | None = None,
    env: Dict[str, str] | None = None,
    stdout_path: Path | None = None,
    stderr_to_stdout: bool = True,
    check: bool = True,
    append: bool = False,
) -> subprocess.CompletedProcess:
    """
    Run a subprocess and optionally capture or tee stdout to a file.

    Args:
      args: Command and arguments.
      cwd: Working directory for the process.
      env: Environment variables to set/override.
      stdout_path: If provided, write stdout to this file (created with parents).
      stderr_to_stdout: If True, merge stderr into stdout.
      check: If True, raise CalledProcessError on non-zero exit.
      append: If True, appends the output to the log file instead of replacing it.

    Returns:
      The CompletedProcess result from subprocess.run.
    """
    # Default: capture stdout; route stderr per flag
    stdout = subprocess.PIPE
    stderr = subprocess.STDOUT if stderr_to_stdout else subprocess.PIPE

    out_file = None
    if stdout_path is not None:
        # Ensure destination exists and stream stdout directly to file
        stdout_path.parent.mkdir(parents=True, exist_ok=True)
        mode = "ab" if append else "wb"
        out_file = open(stdout_path, mode)
        stdout = out_file
        # Keep stderr routing consistent with stderr_to_stdout flag
        stderr = subprocess.STDOUT if stderr_to_stdout else subprocess.PIPE

    try:
        return subprocess.run(
            args,
            cwd=str(cwd) if cwd else None,
            env=env,
            stdout=stdout,
            stderr=stderr,
            check=check,
        )
    finally:
        # Close file handle if we opened one
        if out_file is not None:
            out_file.close()


def sh_quote(s: str) -> str:
    """POSIX-shell-quote a string so it can be safely embedded in a command line."""
    return shlex.quote(s)


def atomic_create_text(path: Path, content: str) -> None:
    """
    Atomically create a new UTF-8 text file; fail if the path already exists.

    Notes:
      - Uses O_CREAT|O_EXCL to guarantee exclusive creation.
      - File mode is 0644 (subject to umask).
    """
    ensure_dir(path.parent)
    fd = os.open(str(path), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(content)
