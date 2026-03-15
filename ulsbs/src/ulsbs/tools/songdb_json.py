# SPDX-FileCopyrightText: 2016-2026 Lari Natri <lari.natri@iki.fi>
# SPDX-License-Identifier: GPL-3.0-or-later

"""
CLI helper to dump song/chapter metadata as JSON.

This tool parses a songbook main .tex file (optionally already processed with
lilypond-book), follows \\input / \\include directives and prints the resulting
ulsbs.songdb.SongbookData class as JSON.

Usage (after installing the ulsbs package):

    ulsbs-songdb-json path/to/main.tex > songdb.json

You can also invoke it directly as a module:

    PYTHONPATH=ulsbs/src python3 -m ulsbs.tools.songdb_json path/to/main.tex > songdb.json
"""

from __future__ import annotations

from dataclasses import asdict
import argparse
import json
import os
import sys
from pathlib import Path
from typing import Iterable, List

from ..songdb import build_song_database


def _build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="ulsbs-songdb-json",
        description="Parse a songbook main TeX file and output song/chapter metadata as JSON.",
    )

    p.add_argument(
        "main_tex",
        metavar="MAIN_TEX",
        help="Main songbook TeX file (typically the same one you'd pass to ulsbs-compile)",
    )
    p.add_argument(
        "-I",
        "--include-dir",
        action="append",
        dest="include_dirs",
        default=None,
        help=(
            "Additional directory to search for \\input / \\include files. "
            "Can be given multiple times. If omitted, only the directory of MAIN_TEX is used."
        ),
    )
    p.add_argument(
        "-o",
        "--output",
        type=Path,
        help=(
            "Write JSON to this file instead of stdout. Parent directory "
            "must already exist."
        ),
    )

    return p


def _parse_texinputs_env() -> List[Path]:
    """Return directories from the TEXINPUTS environment variable.

    TEXINPUTS uses ':' as a separator. Empty segments mean "use the default
    TeX search path"; we ignore those here and only care about explicit
    directories. A trailing '//' on a segment means "search recursively"
    for TeX, but this helper just treats it as the same directory.
    """

    raw = os.environ.get("TEXINPUTS")
    if not raw:
        return []

    dirs: List[Path] = []
    for part in raw.split(":"):
        part = part.strip()
        if not part:
            # Skip empty entries (TeX's "default" path markers)
            continue
        if part.endswith("//"):
            # Ignore TeX's recursive semantics; use the underlying directory
            part = part[:-2] or "."
        p = Path(part).expanduser().resolve()
        dirs.append(p)
    return dirs


def _normalise_include_dirs(main_tex: Path, include_dirs: Iterable[str] | None) -> List[Path]:
    """Build the include search path list.

    Order (from highest to lowest precedence during lookup):
      1. Directory of the main TeX file
      2. Directories given explicitly via -I / --include-dir (in CLI order)
      3. Directories from the TEXINPUTS environment variable (in env order)
    """

    # 1. Always search in the main document directory first
    main_dir = main_tex.parent.resolve()
    dirs: List[Path] = [main_dir]

    # 2. Explicit -I paths
    cli_dirs: List[Path] = []
    if include_dirs:
        for d in include_dirs:
            if d:
                cli_dirs.append(Path(d).expanduser().resolve())

    # 3. TEXINPUTS paths
    env_dirs = _parse_texinputs_env()

    # Deduplicate while preserving order, keeping main_dir first and ensuring
    # explicitly given -I paths come before TEXINPUTS paths.
    seen = {main_dir}
    for group in (cli_dirs, env_dirs):
        for p in group:
            if p not in seen:
                dirs.append(p)
                seen.add(p)

    return dirs


def main(argv: list[str] | None = None) -> int:

    parser = _build_arg_parser()
    ns = parser.parse_args(argv)

    try:

        main_tex = Path(ns.main_tex).expanduser().resolve()

        if not main_tex.exists():
            raise FileNotFoundError(f"File not found: {ns.main_tex}")
        if not main_tex.is_file():
            raise RuntimeError(f"Not a regular file: {ns.main_tex}")

        include_dirs = _normalise_include_dirs(main_tex, ns.include_dirs)

        # Build the db from TeX tree
        db = build_song_database(processed_tex=main_tex, include_search_paths=include_dirs)

        def _default(obj):
            if isinstance(obj, Path):
                return obj.as_posix()
            raise TypeError(f"Object of type {type(obj).__name__} is not JSON-serialisable")

        raw = asdict(db)
        json_text = json.dumps(raw, default=_default, indent=2, ensure_ascii=False)

        if ns.output:
            ns.output.write_text(json_text + "\n", encoding="utf-8")
        else:
            # Print to stdout
            print(json_text)

        return 0

    except Exception as e:

        print(f"Error: {str(e)}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
