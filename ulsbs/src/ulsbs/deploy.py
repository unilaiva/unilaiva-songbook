# SPDX-FileCopyrightText: 2016-2026 Lari Natri <lari.natri@iki.fi>
# SPDX-License-Identifier: GPL-3.0-or-later

"""
Deploy compiled artifacts to the deploy directory.
This file is part of the 'ulsbs' package.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from .config import Config

from .constants import (
    RESULTLIST_SEPARATOR,
    RESULT_TYPE_MAIN_PDF,
    RESULT_TYPE_PRINTOUT_PDF,
    RESULT_TYPE_IMAGE,
    RESULT_TYPE_MIDIDIR,
    RESULT_TYPE_AUDIODIR,
    RESULT_TYPE_COMMONICON,
    RESULT_TYPE_COMMONMETADATA,
    RESULT_TYPE_COMMONOTHER,
    RESULT_PRINTOUT_SUBDIRNAME,
    RESULT_IMAGE_SUBDIRNAME,
    RESULT_MIDI_SUBDIRNAME,
    RESULT_AUDIO_SUBDIRNAME,
    DEPLOY_IMAGE_SUBDIRNAME,
    DEPLOY_PRINTOUT_SUBDIRNAME,
    DEPLOY_AUDIO_SUBDIRNAME,
    DEPLOY_MIDI_SUBDIRNAME,
    DEPLOY_COMMONICON_SUBDIRNAME,
    DEPLOY_COMMONMETADATA_SUBDIRNAME,
    DEPLOY_COMMONOTHER_SUBDIRNAME,
    NODEPLOY_FNAMEPART,
)
import ulsbs.resultlist as resultlist
from .ui import UI
from .util import ensure_dir, files_are_identical, sync_tree


def deploy_results(ui: UI, cfg: Config) -> None:
    """Copy results from result/ to deploy/, respecting result list entries."""
    result_dir = cfg.runtime.project_paths.result_dir
    deploy_dir = cfg.deploy_dir

    if cfg.runtime.in_container:
        return

    if not resultlist.exists():
        ui.nodeploy_line("Nothing to deploy!")
        return

    if not deploy_dir.exists():
        ui.nodeploy_line("Results NOT copied to deploy directory.")
        ui.space_line(f"Directory not found: {str(deploy_dir)}")
        return

    # Append common files to the deploy list if not there already, with abs path
    for icon in sorted(cfg.common_deploy_icons):
        resultlist.append_line_if_missing(RESULT_TYPE_COMMONICON, icon)
    for md in sorted(cfg.common_deploy_metadata):
        resultlist.append_line_if_missing(RESULT_TYPE_COMMONMETADATA, md)
    for oth in sorted(cfg.common_deploy_other):
        resultlist.append_line_if_missing(RESULT_TYPE_COMMONOTHER, oth)

    skipped = 0
    for line in resultlist.lines():
        if not line.strip():
            continue
        try:
            ftype, fname = line.split(RESULTLIST_SEPARATOR, 1)
        except ValueError:
            ui.warning_line(f"Skipping deformed result list line: {line}")
            continue

        if NODEPLOY_FNAMEPART in fname:
            ui.nodeploy_line(f"{fname} not deployed due to filename")
            continue

        if cfg.deploy_common and ftype not in (
            RESULT_TYPE_COMMONICON,
            RESULT_TYPE_COMMONMETADATA,
            RESULT_TYPE_COMMONOTHER,
        ):
            continue

        if ftype == RESULT_TYPE_MAIN_PDF:
            src = result_dir / fname
            dst_dir = deploy_dir
        elif ftype == RESULT_TYPE_PRINTOUT_PDF:
            src = result_dir / RESULT_PRINTOUT_SUBDIRNAME / fname
            dst_dir = deploy_dir / DEPLOY_PRINTOUT_SUBDIRNAME
        elif ftype == RESULT_TYPE_IMAGE:
            src = result_dir / RESULT_IMAGE_SUBDIRNAME / fname
            dst_dir = deploy_dir / DEPLOY_IMAGE_SUBDIRNAME
        elif ftype == RESULT_TYPE_COMMONICON:
            src = Path(fname)
            dst_dir = deploy_dir / DEPLOY_COMMONICON_SUBDIRNAME
        elif ftype == RESULT_TYPE_COMMONMETADATA:
            src = Path(fname)
            dst_dir = deploy_dir / DEPLOY_COMMONMETADATA_SUBDIRNAME
        elif ftype == RESULT_TYPE_COMMONOTHER:
            src = Path(fname)
            dst_dir = deploy_dir / DEPLOY_COMMONOTHER_SUBDIRNAME
        elif ftype == RESULT_TYPE_MIDIDIR:
            src = result_dir / RESULT_MIDI_SUBDIRNAME / fname
            dst_dir = deploy_dir / DEPLOY_MIDI_SUBDIRNAME / fname
        elif ftype == RESULT_TYPE_AUDIODIR:
            src = result_dir / RESULT_AUDIO_SUBDIRNAME / fname
            dst_dir = deploy_dir / DEPLOY_AUDIO_SUBDIRNAME / fname
        else:
            continue

        if not src.exists():
            ui.warning_line(f"Could not access {src} for deployment")
            continue

        ensure_dir(dst_dir)

        # dir
        if src.is_dir():
            # Synchronize directory contents without overwriting identical files
            # and remove entries in the destination that no longer exist in the
            # source tree.
            skipped += sync_tree(src, dst_dir)
            ui.deploy_line(f"{dst_dir.parent.name}/{dst_dir.name}/")
            continue

        # single file
        dst = dst_dir / src.name
        if dst.exists():
            try:
                if files_are_identical(src, dst):
                    skipped += 1
                    continue
            except Exception:
                pass
        shutil.copy2(src, dst)

        try:
            display_path = dst.relative_to(deploy_dir)
        except ValueError:
            display_path = dst
        ui.deploy_line(str(display_path))

    if skipped:
        ui.nodeploy_line(
            f"Skipped {skipped} existing identical file{'s' if skipped != 1 else ''} during deploy"
        )

    resultlist.delete()
