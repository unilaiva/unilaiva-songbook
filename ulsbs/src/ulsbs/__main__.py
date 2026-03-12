# SPDX-FileCopyrightText: 2016-2026 Lari Natri <lari.natri@iki.fi>
# SPDX-License-Identifier: GPL-3.0-or-later

"""
Module entry point for `python -m ulsbs`.
This file is part of the 'ulsbs' package.
"""

# Test for python version before importing any package modules.
import sys
REQUIRED = (3, 11)
if sys.version_info < REQUIRED:
    sys.stderr.write(
        "ulsbs requires Python {}.{}+, but you are running {}.{}.{}\n".format(
            REQUIRED[0], REQUIRED[1], *sys.version_info[:3]
        )
    )
    raise SystemExit(1)

from .cli import main

if __name__ == "__main__":
    raise SystemExit(main())
