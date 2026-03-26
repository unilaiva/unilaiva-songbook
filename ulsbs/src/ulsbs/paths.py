# SPDX-FileCopyrightText: 2016-2026 Lari Natri <lari.natri@iki.fi>
# SPDX-License-Identifier: GPL-3.0-or-later

"""
Resolve important project paths (temp, result, deploy, content, etc.).
This file is part of the 'ulsbs' package.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import List

from .constants import (
    TEMP_DIRNAME,
    RESULT_DIRNAME,
    DEPLOY_DIRNAME,
    CONTENT_DIRNAME,
    INCLUDE_DIRNAME,
    CONFIG_FILENAME,
)


@dataclass(frozen=True)
class ProjectPaths:
    """Container for key directories and files in a project root."""

    project_root: Path
    host_project_root: Path
    config_file: Path
    temp_dir: Path
    result_dir: Path
    deploy_dir: Path
    content_dir: Path
    include_dir: Path

    @staticmethod
    def from_root(project_root: Path) -> ProjectPaths:
        """Create ProjectPaths from an explicit project root."""
        project_root = project_root.resolve()
        host_project_root_from_env = os.environ.get("ULSBS_INTERNAL_PROJECT_ROOT_ON_HOST", "") or ""
        if host_project_root_from_env == "":
            host_project_root = project_root
        else:
            host_project_root = Path(host_project_root_from_env)
        config_file = project_root / CONFIG_FILENAME
        if not (config_file.exists() and config_file.is_file()):
            raise SystemExit(
                f"Config file not found: {config_file}.Please create one; it can be empty."
            )
        temp_dir = project_root / TEMP_DIRNAME
        result_dir = project_root / RESULT_DIRNAME
        deploy_dir = project_root / DEPLOY_DIRNAME
        content_dir = project_root / CONTENT_DIRNAME
        include_dir = project_root / INCLUDE_DIRNAME

        return ProjectPaths(
            project_root=project_root,
            host_project_root=host_project_root,
            config_file=config_file,
            temp_dir=temp_dir,
            result_dir=result_dir,
            deploy_dir=deploy_dir,
            content_dir=content_dir,
            include_dir=include_dir,
        )

    @staticmethod
    def from_docs(explicit_docs: List[Path] | None = None) -> ProjectPaths:
        """
        Create ProjectPaths from a set of main document paths.

        - If explicit_docs is None or empty, the current working directory is
          treated as the project root, and must contain CONFIG_FILENAME.
        - If explicit_docs is non-empty, the documents may live in different
          directories, but they must share a common ancestor directory that
          contains CONFIG_FILENAME.  Among all such common ancestors, the
          closest one is chosen as the project root.
        """
        # No explicit docs: assume CWD to be the project root
        if not explicit_docs:
            return ProjectPaths.from_root(Path.cwd())

        # Resolve all document paths and collect their parent directories.
        #
        # We deliberately use .absolute() instead of .resolve() so that
        # symlinked main documents are located by the directory where the
        # symlink lives, not by the directory of the final target. This
        # allows a project root containing CONFIG_FILENAME to be discovered
        # even when the main TeX file is a symlink that points outside the
        # project tree.
        doc_parents = [p.absolute().parent for p in explicit_docs]

        # Precompute ancestor sets for fast membership tests.  Order is
        # determined solely by walking upwards from the first document's
        # directory; sets are used only for membership, not ordering.
        def _ancestor_chain(start: Path) -> list[Path]:
            out: list[Path] = []
            cur = start
            while True:
                out.append(cur)
                if cur.parent == cur:
                    break
                cur = cur.parent
            return out

        parent_anc_sets = [{a for a in _ancestor_chain(parent)} for parent in doc_parents]

        # Walk upwards from the first document's directory towards the root.
        # The first directory that is a common ancestor of all documents and
        # contains CONFIG_FILENAME is the deepest suitable project root.
        for candidate in _ancestor_chain(doc_parents[0]):
            if all(candidate in anc for anc in parent_anc_sets):
                cfg = candidate / CONFIG_FILENAME
                if cfg.is_file():
                    return ProjectPaths.from_root(candidate)

        if len(explicit_docs) == 1:
            raise SystemExit(
                f"No {CONFIG_FILENAME} found. Please create one in the project's root; "
                "it can be empty."
            )
        else:
            raise SystemExit(
                f"No common ancestor directory with {CONFIG_FILENAME} "
                "found for documents: "
                f"{sorted(str(p) for p in explicit_docs)}. "
                f"Please create {CONFIG_FILENAME} in the project's root; it can be empty."
            )
