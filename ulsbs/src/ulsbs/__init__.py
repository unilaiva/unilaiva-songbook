# SPDX-FileCopyrightText: 2016-2026 Lari Natri <lari.natri@iki.fi>
# SPDX-License-Identifier: GPL-3.0-or-later

"""
Package init; exposes package version.
This file is part of the 'ulsbs' package.
"""

from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("ulsbs")
except PackageNotFoundError:
    __version__ = "0.0.0"

__all__ = ["__version__"]
