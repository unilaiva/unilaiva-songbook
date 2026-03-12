# SPDX-FileCopyrightText: 2016-2026 Lari Natri <lari.natri@iki.fi>
# SPDX-License-Identifier: GPL-3.0-or-later

"""
Resolve important project paths (temp, result, deploy, content, etc.).
This file is part of the 'ulsbs' package.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List

from .constants import (
    TEMP_DIRNAME, RESULT_DIRNAME, DEPLOY_DIRNAME, CONTENT_DIRNAME,
    INCLUDE_DIRNAME, RESULTLIST_BASENAME,
)


@dataclass(frozen=True)
class ProjectPaths:
    """Container for key directories and files in a project root."""
    project_root: Path
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
        config_file = project_root / "ulsbs-config.toml"
        if not (config_file.exists() and config_file.is_file()):
            raise SystemExit(f"Config file not found: {config_file}")
        temp_dir = project_root / TEMP_DIRNAME
        result_dir = project_root / RESULT_DIRNAME
        deploy_dir = project_root / DEPLOY_DIRNAME
        content_dir = project_root / CONTENT_DIRNAME
        include_dir = project_root / INCLUDE_DIRNAME

        return ProjectPaths(
            project_root=project_root,
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
        Create ProjectPaths from explicit docs. If none, use the CWD.
        """
        project_root = Path.cwd().resolve()
        if explicit_docs:
            parents = {p.resolve().parent for p in explicit_docs}
            if len(parents) != 1:
                raise SystemExit(
                    "Documents are not in the same directory: "
                    f"{sorted(str(x) for x in parents)}"
                )
            project_root = next(iter(parents))
        return ProjectPaths.from_root(project_root)
