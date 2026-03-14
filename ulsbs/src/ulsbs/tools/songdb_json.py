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


def _normalise_include_dirs(main_tex: Path, include_dirs: Iterable[str] | None) -> List[Path]:
    # Always search in the main document directory first
    dirs: List[Path] = [main_tex.parent.resolve()]
    if include_dirs:
        for d in include_dirs:
            if d:
                dirs.append(Path(d).resolve())
    return dirs


def main(argv: list[str] | None = None) -> int:
    parser = _build_arg_parser()
    ns = parser.parse_args(argv)

    main_tex = Path(ns.main_tex).expanduser().resolve()
    include_dirs = _normalise_include_dirs(main_tex, ns.include_dirs)

    db = build_song_database(processed_tex=main_tex, include_search_paths=include_dirs)

    def _default(obj):  # type: ignore[override]
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


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
