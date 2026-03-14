# SPDX-FileCopyrightText: 2016-2026 Lari Natri <lari.natri@iki.fi>
# SPDX-License-Identifier: GPL-3.0-or-later

"""
Access packaged assets (tex, img, docker contexts).
This file is part of the 'ulsbs' package.
"""

from __future__ import annotations

import shutil
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from typing import Iterator


@dataclass(frozen=True)
class EngineAssets:
    """
    Access non-Python assets packaged under ulsbs/assets/.

    Use context managers because assets may be inside a wheel and need
    temporary extraction (importlib.resources.as_file()).
    """
    package: str = "ulsbs"
    assets_dirname: str = "assets"

    def _root(self):
        """Return the assets root resources handle."""
        return resources.files(self.package) / self.assets_dirname

    @contextmanager
    def tex_dir(self) -> Iterator[Path]:
        """Yield the TeX assets directory (Path)."""
        ref = self._root() / "tex"
        with resources.as_file(ref) as p:
            yield p

    @contextmanager
    def ly_dir(self) -> Iterator[Path]:
        """Yield the Lilypond assets directory (Path)."""
        ref = self._root() / "ly"
        with resources.as_file(ref) as p:
            yield p

    @contextmanager
    def img_dir(self) -> Iterator[Path]:
        """Yield the image assets directory (Path)."""
        ref = self._root() / "img"
        with resources.as_file(ref) as p:
            yield p

    @contextmanager
    def docker_context(self, name: str = "ulsbs-compiler") -> Iterator[Path]:
        """Yield a Docker build context directory by name."""
        ref = self._root() / "docker" / name
        with resources.as_file(ref) as p:
            yield p

    @contextmanager
    def package_mount_root(self) -> Iterator[Path]:
        """
        Yield a host dir to add to PYTHONPATH so 'import ulsbs' works and
        assets are on disk. Cleans up temp dirs automatically.
        """
        # Fast path: package lives on disk with assets as a normal directory
        pkg_dir = Path(__file__).resolve().parent
        py_root = pkg_dir.parent
        if (pkg_dir / self.assets_dirname).is_dir():
            yield py_root
            return

        # Fallback: materialize the entire package into a temp dir (works for zip-imports)
        tmp_base = Path(tempfile.mkdtemp(prefix="ulsbs_pkg_"))
        out_pkg = tmp_base / self.package
        out_pkg.mkdir(parents=True, exist_ok=True)

        # Use importlib.resources to access the package contents even when zip-imported,
        # then copy the whole tree (code + assets) into our temp package dir.
        with resources.as_file(resources.files(self.package)) as pkg_src:
            shutil.copytree(pkg_src, out_pkg, dirs_exist_ok=True)

        try:
            yield tmp_base
        finally:
            shutil.rmtree(tmp_base, ignore_errors=True)
