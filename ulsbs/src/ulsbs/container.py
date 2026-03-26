# SPDX-FileCopyrightText: 2016-2026 Lari Natri <lari.natri@iki.fi>
# SPDX-License-Identifier: GPL-3.0-or-later

"""
Container integration: build image and run the compiler inside it.
This file is part of the 'ulsbs' package.
"""

from __future__ import annotations

import datetime as _dt
import os
import secrets
import subprocess
from pathlib import Path
from typing import List

import ulsbs  # for getting version (though we are already inside the package)

from .config import Config
from .engine_assets import EngineAssets
from .ui import UI
from .util import sh_quote, which

_CONTAINER_IMAGE_NAME = "ulsbs-compiler"
_HOMECACHE_VOLUME_NAME = "ulsbs-compiler-homecache"


def _pick_container_engine(cfg: Config) -> str:
    """Choose container engine ('auto', 'docker', or 'podman').

    Semantics:
      - 'auto'   (recommended/default): prefer Docker if available, else Podman.
      - 'docker' : require Docker; do not fall back to Podman.
      - 'podman' : require Podman.
    """
    requested_raw = (cfg.container_engine or "auto").strip()
    requested = requested_raw.lower()

    if requested not in {"auto", "docker", "podman"}:
        raise RuntimeError(
            f"Unsupported container engine: {requested_raw!r} (expected 'auto', 'docker' or 'podman')"
        )

    if requested == "auto":
        if which("docker") is not None:
            return "docker"
        if which("podman") is not None:
            return "podman"
        raise RuntimeError(
            "No container engine found (tried 'docker' and 'podman'). "
            "Install one or use --no-container."
        )

    if requested == "docker":
        if which("docker") is not None:
            return "docker"
        raise RuntimeError(
            "Docker executable not found. Install Docker, use 'podman' or 'auto', or use --no-container."
        )

    # requested == "podman"
    if which("podman") is not None:
        return "podman"
    raise RuntimeError(
        "Podman executable not found. Install Podman, use 'docker' or 'auto', or use --no-container."
    )


def container_image_exists(engine: str) -> bool:
    """Return True if our container image exists locally for the given engine."""
    try:
        out = subprocess.check_output(
            [engine, "image", "ls", "-q", _CONTAINER_IMAGE_NAME],
            text=True,
        ).strip()
        return bool(out)
    except Exception:
        return False


def container_image_created_ts(engine: str) -> int | None:
    """Return image creation time (UTC, epoch seconds), or None on error."""
    try:
        created = subprocess.check_output(
            [engine, "inspect", "-f", "{{ .Created }}", _CONTAINER_IMAGE_NAME],
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


def ensure_container_image(ui: UI, assets: EngineAssets, engine: str, force_rebuild: bool) -> None:
    """Build or rebuild the container image when needed."""
    build_needed = force_rebuild

    with assets.container_context(_CONTAINER_IMAGE_NAME) as ctx:
        if not build_needed:
            if not container_image_exists(engine):
                build_needed = True
            else:
                img_ts = container_image_created_ts(engine)
                df_ts = dockerfile_mtime_ts(ctx / "Dockerfile")
                if img_ts is not None and df_ts is not None and df_ts > img_ts:
                    build_needed = True
        if build_needed:
            ui.container_line("Build compiler image...")

            # Reset compiler home cache volume when rebuilding the image.
            # Ignore any errors (e.g. volume doesn't exist or engine doesn't support volumes).
            try:
                subprocess.run(
                    [engine, "volume", "rm", _HOMECACHE_VOLUME_NAME],
                    check=False,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            except Exception:
                pass

            version = getattr(ulsbs, "__version__", "unknown")
            build_cmd = [
                engine,
                "build",
                "--no-cache",
                "--build-arg",
                f"BUILT_BY_ULSBS_VERSION={version}",
                "-t",
                _CONTAINER_IMAGE_NAME,
                str(ctx),
            ]
            subprocess.run(build_cmd, check=True)
            ui.container_line("Building image complete.")


def run_self_in_container(
    ui: UI,
    assets: EngineAssets,
    cfg: Config,
    passthrough_args: List[str],
    script_file: Path,
) -> int:
    """Run the current CLI inside a container and return its exit code."""

    unique_id = cfg.runtime.unique_id
    proj = cfg.runtime.project_paths
    container_rebuild = cfg.container_rebuild
    container_memory_gb = cfg.container_memory_gb
    container_memory_plus_swap_gb = cfg.container_memory_plus_swap_gb
    shell_only = cfg.shell

    memory_arg = f"{container_memory_gb}g"
    memory_swap_arg = f"{container_memory_plus_swap_gb}g"

    engine = _pick_container_engine(cfg)
    ensure_container_image(ui, assets, engine, container_rebuild)

    container_workdir = "/songbook-data"
    mount_root = proj.project_root.resolve()
    mount_temp = (proj.project_root / "temp").resolve()

    with assets.package_mount_root() as py_root:
        env_args = [
            "-e",
            f"ULSBS_MAX_PARALLEL={os.environ.get('ULSBS_MAX_PARALLEL', '')}",
            "-e",
            f"ULSBS_MAX_CONTAINER_MEM_GB={os.environ.get('ULSBS_MAX_CONTAINER_MEM_GB', '')}",
            "-e",
            f"ULSBS_USE_SYSTEM_TMP_FOR_TEMP={os.environ.get('ULSBS_USE_SYSTEM_TMP_FOR_TEMP', '')}",
            "-e",
            f"ULSBS_CONTAINER_ENGINE={engine}",
            "-e",
            "ULSBS_INTERNAL_RUNNING_IN_CONTAINER=true",
            "-e",
            f"ULSBS_INTERNAL_UNIQUE_ID={unique_id}",
            "-e",
            f"ULSBS_INTERNAL_PROJECT_ROOT_ON_HOST={proj.project_root}",
        ]

        bind_py = f"type=bind,src={str(py_root)},dst=/ulsbs-py,ro"
        bind_root = f"type=bind,src={str(mount_root)},dst={container_workdir}"
        bind_temp = f"type=bind,src={str(mount_temp)},dst={container_workdir}/temp"
        if engine == "podman":
            bind_py += ",Z"
            bind_root += ",Z"
            bind_temp += ",Z"

        container_name = f"{_CONTAINER_IMAGE_NAME}-{secrets.token_hex(4)}"
        container_args = [
            engine,
            "run",
            "--name",
            container_name,
            "-it",
            "--rm",
            "--read-only",
            *env_args,
            "--memory",
            memory_arg,
            "--memory-swap",
            memory_swap_arg,
            "--user",
            f"{os.getuid()}:{os.getgid()}",
            "--mount",
            bind_py,
            "--mount",
            bind_root,
            "--mount",
            bind_temp,
            "--mount",
            f"type=volume,src={_HOMECACHE_VOLUME_NAME},dst=/home/ulsbs",
            "--mount",
            "type=tmpfs,tmpfs-size=128m,dst=/tmp",
            "--mount",
            "type=tmpfs,tmpfs-size=16m,dst=/run",
            _CONTAINER_IMAGE_NAME,
        ]

        # Bind host timezone data to container for correct localtime
        try:
            insert_pos = container_args.index(_CONTAINER_IMAGE_NAME)
        except ValueError:
            insert_pos = len(container_args)
        try:
            host_localtime = Path("/etc/localtime")
            if host_localtime.exists():
                resolved_localtime = host_localtime.resolve()
                tz_mount = f"type=bind,src={str(resolved_localtime)},dst=/etc/localtime,ro"
                if engine == "podman":
                    tz_mount += ",Z"
                container_args[insert_pos:insert_pos] = [
                    "--mount",
                    tz_mount,
                ]
                insert_pos += 2
        except Exception:
            pass

        # Strip args not for container
        inner_args = [a for a in passthrough_args if a not in ("")]

        inner = f"cd {container_workdir} && PYTHONPATH=/ulsbs-py python3 -m ulsbs " + " ".join(
            sh_quote(a) for a in inner_args
        )

        if shell_only:
            inner = f"cd {container_workdir} && PYTHONPATH=/ulsbs-py bash"

        container_args.extend(["bash", "-lc", inner])
        ui.container_line(f"Start compiler container using {engine}")
        cp = subprocess.run(container_args)
    return int(cp.returncode)
