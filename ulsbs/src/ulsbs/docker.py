# SPDX-FileCopyrightText: 2016-2026 Lari Natri <lari.natri@iki.fi>
# SPDX-License-Identifier: GPL-3.0-or-later

"""
Docker integration: build image and run the compiler inside it.
This file is part of the 'ulsbs' package.
"""

from __future__ import annotations

import datetime as _dt
import os
import subprocess
from pathlib import Path
from typing import List

import ulsbs  # for getting version (though we are already inside the package)

from .config import Config
from .paths import ProjectPaths
from .ui import UI
from .util import run_cmd, sh_quote, which

_DOCKER_IMAGE_NAME = "ulsbs-compiler"


def docker_image_exists() -> bool:
    """Return True if our Docker image exists locally."""
    try:
        out = subprocess.check_output(
            ["docker", "image", "ls", "-q", _DOCKER_IMAGE_NAME],
            text=True,
        ).strip()
        return bool(out)
    except Exception:
        return False


def docker_image_created_ts() -> int | None:
    """Return image creation time (UTC, epoch seconds), or None on error."""
    try:
        created = subprocess.check_output(
            ["docker", "inspect", "-f", "{{ .Created }}", _DOCKER_IMAGE_NAME],
            text=True,
        ).strip()
        created = created.replace("Z", "+00:00")
        dt = _dt.datetime.fromisoformat(created)
        return int(dt.timestamp())
    except Exception:
        return None


def dockerfile_mtime_ts(dockerfile: Path) -> int | None:
    """Return Dockerfile mtime (epoch seconds), or None on error."""
    try:
        return int(dockerfile.stat().st_mtime)
    except Exception:
        return None


def ensure_docker_image(ui: UI, assets: EngineAssets, force_rebuild: bool) -> None:
    """Build or rebuild the Docker image when needed."""
    if which("docker") is None:
        raise RuntimeError(
            "Docker executable not found. Install Docker or use --no-docker argument."
        )

    build_needed = force_rebuild

    with assets.docker_context(_DOCKER_IMAGE_NAME) as ctx:
        if not build_needed:
            if not docker_image_exists():
                build_needed = True
            else:
                img_ts = docker_image_created_ts()
                df_ts = dockerfile_mtime_ts(ctx / "Dockerfile")
                if img_ts is not None and df_ts is not None and df_ts > img_ts:
                    build_needed = True
        if build_needed:
            ui.docker_line("Build compiler image...")
            version = getattr(ulsbs, "__version__", "unknown")
            subprocess.run(
                [
                    "docker", "build", "--no-cache",
                    "--build-arg", f"BUILT_BY_ULSBS_VERSION={version}",
                    "-t", _DOCKER_IMAGE_NAME, str(ctx),
                ],
                check=True,
            )
            ui.docker_line("Building image complete.")


def run_self_in_docker(
    ui: UI,
    assets: EngineAssets,
    cfg: Config,
    passthrough_args: List[str],
    script_file: Path,
) -> int:
    """Run the current CLI inside the Docker container and return its code."""

    unique_id = cfg.runtime.unique_id
    proj = cfg.runtime.project_paths
    docker_rebuild = cfg.docker_rebuild
    docker_memory = cfg.docker_memory
    docker_memory_plus_swap = cfg.docker_memory_plus_swap
    shell_only = cfg.shell

    ensure_docker_image(ui, assets, docker_rebuild)

    container_workdir = "/songbook-data"
    mount_root = proj.project_root.resolve()
    mount_temp = (proj.project_root / "temp").resolve()

    with assets.package_mount_root() as py_root:
        env_args = [
            "-e", f"ULSBS_MAX_PARALLEL={os.environ.get('ULSBS_MAX_PARALLEL','')}",
            "-e", f"ULSBS_MAX_DOCKER_MEMORY={os.environ.get('ULSBS_MAX_DOCKER_MEMORY','')}",
            "-e", f"ULSBS_USE_SYSTEM_TMP_FOR_TEMP={os.environ.get('ULSBS_USE_SYSTEM_TMP_FOR_TEMP','')}",
            "-e", "ULSBS_INTERNAL_RUNNING_IN_CONTAINER=true",
            "-e", f"ULSBS_INTERNAL_UNIQUE_ID={unique_id}"
        ]

        docker_args = [
            "docker", "run", "-it", "--rm", "--read-only",
            *env_args,
            "--memory", docker_memory,
            "--memory-swap", docker_memory_plus_swap,
            "--user", f"{os.getuid()}:{os.getgid()}",
            "--mount", f"type=bind,src={str(py_root)},dst=/ulsbs-py,ro",
            "--mount", f"type=bind,src={str(mount_root)},dst={container_workdir}",
            "--mount", f"type=bind,src={str(mount_temp)},dst={container_workdir}/temp",
            "--mount", "type=volume,src=ulsbs-compiler-homecache,dst=/home/ulsbs",
            "--mount", "type=tmpfs,tmpfs-size=128m,dst=/tmp",
            "--mount", "type=tmpfs,tmpfs-size=16m,dst=/run",
            _DOCKER_IMAGE_NAME,
        ]

        # Optionally bind host timezone data to container for correct localtime
        try:
            insert_pos = docker_args.index(_DOCKER_IMAGE_NAME)
        except ValueError:
            insert_pos = len(docker_args)
        try:
            host_localtime = Path("/etc/localtime")
            if host_localtime.exists():
                resolved_localtime = host_localtime.resolve()
                docker_args[insert_pos:insert_pos] = [
                    "--mount", f"type=bind,src={str(resolved_localtime)},dst=/etc/localtime,ro",
                ]
                insert_pos += 2
            host_zoneinfo = Path("/usr/share/zoneinfo")
            if host_zoneinfo.exists():
                docker_args[insert_pos:insert_pos] = [
                    "--mount", f"type=bind,src={str(host_zoneinfo)},dst=/usr/share/zoneinfo,ro",
                ]
                insert_pos += 2
        except Exception:
            pass

        try:
            script_rel = script_file.resolve().relative_to(proj.project_root.resolve())
        except Exception:
            script_rel = script_file.name

        # Strip args not for docker container
        inner_args = [a for a in passthrough_args if a not in ("")]

        inner = (
            f"cd {container_workdir} && "
            f"PYTHONPATH=/ulsbs-py "
            f"python3 -m ulsbs "
            + " ".join(sh_quote(a) for a in inner_args)
        )

        if shell_only:
            inner = (
                f"cd {container_workdir} && "
                f"PYTHONPATH=/ulsbs-py "
                f"bash"
            )

        docker_args.extend(["bash", "-lc", inner])
        ui.docker_line("Start compiler container")
        cp = subprocess.run(docker_args)
    return int(cp.returncode)
