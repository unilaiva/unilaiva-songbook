# SPDX-FileCopyrightText: 2016-2026 Lari Natri <lari.natri@iki.fi>
# SPDX-License-Identifier: GPL-3.0-or-later

"""
Build compilation jobs and detect variant feasibility.
This file is part of the 'ulsbs' package.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import List

from .config import Config
from .constants import LYRICSONLY_FNAMEPART, CHARANGO_FNAMEPART, BASSCLEF_FNAMEPART, TEMP_DIRNAME
from .util import read_text, regex_documentclass_ulsbs_songbook


@dataclass(frozen=True)
class Job:
    """One compilation job (document + variant + paths/colors)."""
    doc_tex_abs: Path
    doc_stem: str
    variant: str
    color: str
    compile_dir: Path


def variant_possible_lyrics(doc_tex_abs: Path) -> bool:
    """Return True if doc uses ulsbs-songbook class (lyrics variant ok)."""
    t = read_text(doc_tex_abs)

    # Use shared matcher for \\documentclass[...]{ulsbs-songbook*}
    docclass_re = regex_documentclass_ulsbs_songbook()
    return docclass_re.search(t) is not None


def variant_possible_charango(doc_tex_abs: Path) -> bool:
    """Detect marker enabling the charango variant."""
    return "%%%CREATE_VERSION_CHARANGO%%%" in read_text(doc_tex_abs)


def variant_possible_bassclef(doc_tex_abs: Path) -> bool:
    """Detect marker enabling the bass-clef variant."""
    return "%%%CREATE_VERSION_BASSCLEF%%%" in read_text(doc_tex_abs)


def build_variant_basename(original_base: str, insert: str) -> str:
    """Insert variant token before paper suffix like _A5, if present."""
    m = re.search(r"(_A\d)", original_base)
    if not m:
        return original_base + insert
    idx = m.start()
    return original_base[:idx] + insert + original_base[idx:]


def build_job_queue(cfg: Config, doc_colors: List[str]) -> List[Job]:
    """Build jobs for selected songbooks and allowed variants."""
    project_root = cfg.runtime.project_paths.project_root
    jobs: List[Job] = []
    for i, doc in enumerate(cfg.songbooks):
        color = doc_colors[i % len(doc_colors)]
        base = doc.stem
        jobs.append(Job(doc, base, "default", color, project_root / TEMP_DIRNAME / base / "default"))
        if cfg.lyricbooks and variant_possible_lyrics(doc):
            jobs.append(Job(doc, base, "lyrics", color, project_root / TEMP_DIRNAME / base / "lyrics"))
        if cfg.extrainstrumentbooks and variant_possible_charango(doc):
            jobs.append(Job(doc, base, "charango", color, project_root / TEMP_DIRNAME / base / "charango"))
        if cfg.extrainstrumentbooks and variant_possible_bassclef(doc):
            jobs.append(Job(doc, base, "bassclef", color, project_root / TEMP_DIRNAME / base / "bassclef"))
    return jobs
