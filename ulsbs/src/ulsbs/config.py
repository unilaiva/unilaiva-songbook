# SPDX-FileCopyrightText: 2016-2026 Lari Natri <lari.natri@iki.fi>
# SPDX-License-Identifier: GPL-3.0-or-later

"""
Load, merge, and validate configuration.
This file is part of the 'ulsbs' package.
"""

from __future__ import annotations

import os
import re
import glob
import math
import tomllib
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Tuple, Set

from .constants import CONFIG_FILENAME, COVERIMAGE_HEIGHT, ASSUMED_OS_MEM_GB, ASSUMED_JOB_MEM_GB, DEPLOY_DIRNAME
from .ui import UI
from .util import SystemInfo, system_info


# NOTE: We only import the type to avoid runtime dependency cycles
try:
    from .paths import ProjectPaths  # type: ignore
except Exception:  # pragma: no cover
    ProjectPaths = Any  # fallback for type checking in isolation


@dataclass(frozen=True)
class Runtime:
    """Runtime-only values detected/created by the CLI."""

    project_paths: ProjectPaths
    in_container: bool
    unique_id: str
    system_info: SystemInfo


@dataclass(frozen=True)
class ModifiedCoverPaintRect:
    """A rectangle to be painted on the original cover image.

    Coordinates are given as fractions of width/height in the range [0.0, 1.0],
    using a bottom-left origin (0,0). For example, (0, 0, 0.5, 0.5) covers the
    lower-left quarter of the image.
    """

    x1: float
    y1: float
    x2: float
    y2: float


@dataclass(frozen=True)
class ModifiedCoverPngRule:
    """Configuration for creating a modified/widened cover PNG for a songbook."""

    width_multiplier: float
    songbook_filenames: str = "*"
    color: str = "white"
    paint_area_rects: Tuple[ModifiedCoverPaintRect, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class Config:
    """Validated, merged configuration."""

    # General
    profile: str = "default"
    config_path: Path = Path(CONFIG_FILENAME)
    config_dir: Path = Path(".").resolve()

    # Execution
    use_container: bool = True
    container_rebuild: bool = False
    shell: bool = False
    pull: bool = False
    # Container engine: "auto", "docker" or "podman" (default: "auto"; prefers Docker, falls back to Podman)
    container_engine: str = "auto"

    max_parallel: int = 6
    use_system_tmp: bool = False
    clean_temp: bool = True

    # Quick mode (CLI-only; derivations are applied to other fields)
    quick: bool = False

    # Deploy modes
    deploy: bool = True
    deploy_last: bool = False
    deploy_common: bool = False
    # Resolved deploy directory (absolute); may be overridden via config/CLI.
    deploy_dir: Path = Path("deploy")

    # Features
    extrainstrumentbooks: bool = True
    lyricbooks: bool = True
    create_printouts: bool = True
    coverimage: bool = True
    json: bool = True
    midifiles: bool = True
    audiofiles: bool = True
    midifiles_allow_for_optional_variants: bool = False
    audiofiles_allow_for_optional_variants: bool = False
    fast_audio_encode: bool = False

    # Container resources (GiB)
    container_memory_gb: int = 6
    container_memory_plus_swap_gb: int = 6

    # Files (absolute paths, validated to exist)
    songbooks: Tuple[Path, ...] = field(
        default_factory=tuple
    )  # From config, possibly overwritten by CLI
    common_deploy_icons: Tuple[Path, ...] = field(default_factory=tuple)
    common_deploy_metadata: Tuple[Path, ...] = field(default_factory=tuple)
    common_deploy_other: Tuple[Path, ...] = field(default_factory=tuple)

    # Single-file settings (relative to config dir, must exist)
    mididir_readme_file: Path | None = None
    audiodir_readme_file: Path | None = None

    # Cover image
    # Height in pixels for pdftoppm -scale-to-y when extracting the cover.
    # Defaults to constants.COVERIMAGE_HEIGHT.
    cover_image_height: int = int(COVERIMAGE_HEIGHT)
    # Rules for creating modified/widened cover PNGs; only configurable via file.
    modified_cover_png: Tuple[ModifiedCoverPngRule, ...] = field(default_factory=tuple)

    # Miscellaneous
    verbose: bool = False
    max_log_lines: int = 20

    # Runtime-only section
    runtime: Runtime | None = None


# Global config retrieving
# ========================

_last_built_config: Config | None = None


def get_config() -> Config | None:
    """
    Return the most recently built Config or None if build_config() has not
    been yet called.
    """
    return _last_built_config


# Utilities and merging
# =====================

_BOOL_TRUE = {"1", "true", "yes", "on"}
_WILDCARD_RE = re.compile(r"[*?\[]")  # simple check for any glob meta


def _to_bool_env(v: str | None) -> bool | None:
    """Convert env var string to bool, or None if unset/invalid."""
    if v is None:
        return None
    return v.strip().lower() in _BOOL_TRUE


def _to_int_env(v: str | None) -> int | None:
    """Convert env var string to positive int, or None on failure."""
    if v is None:
        return None
    try:
        i = int(v.strip())
        if i < 1:
            raise ValueError
        return i
    except Exception:
        return None


def _clamp(v: Any, lo: int, hi: int, name: str | None = None) -> int:
    """
    Ensure v is an int and clamp it to [lo, hi].
    Raises ValueError if v cannot be interpreted as an int.
    """
    try:
        i = int(v)
    except Exception:
        nm = name or "value"
        raise ValueError(f"{nm} must be an integer, got {type(v).__name__}") from None
    if i < lo:
        return lo
    if i > hi:
        return hi
    return i


def _deep_merge(a: Dict[str, Any], b: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively merge dicts; values in b override/extend those in a."""
    out = dict(a)
    for k, v in b.items():
        if k in out and isinstance(out[k], dict) and isinstance(v, dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def _deep_merge_with_array_concat(
    a: Dict[str, Any], b: Dict[str, Any], merge_keys: Set[str]
) -> Dict[str, Any]:
    """
    Like _deep_merge, but for keys in merge_keys, merge arrays by
    concatenation, preserving order and adding only new items.

    - Non-dicts and keys not in merge_keys are replaced.
    - For merge_keys, both parent and child must be arrays; otherwise error.
    """
    out = dict(a)
    for k, v in b.items():
        if k in out and isinstance(out[k], dict) and isinstance(v, dict):
            out[k] = _deep_merge_with_array_concat(out[k], v, merge_keys)
        else:
            if k in merge_keys:
                if not isinstance(v, (list, tuple)):
                    raise ValueError(f"merge-keys includes {k!r} but its value is not an array")
                base_val = out.get(k)
                if base_val is None:
                    out[k] = list(v)
                else:
                    if not isinstance(base_val, (list, tuple)):
                        raise ValueError(
                            f"merge-keys includes {k!r} but the inherited value is not an array"
                        )
                    merged_list = list(base_val)
                    for item in v:
                        if item not in merged_list:
                            merged_list.append(item)
                    out[k] = merged_list
            else:
                out[k] = v
    return out


def _normalize_keys(d: Dict[str, Any]) -> Dict[str, Any]:
    """Make keys snake_case by replacing '-' with '_', recursively."""
    out: Dict[str, Any] = {}
    for k, v in d.items():
        nk = k.replace("-", "_") if isinstance(k, str) else k
        if isinstance(v, dict):
            v = _normalize_keys(v)
        if nk in out:
            raise ValueError(f"Duplicate key after normalization: {nk!r}")
        out[nk] = v
    return out


def _apply_negations(d: Dict[str, Any]) -> Dict[str, Any]:
    """
    Support 'no_*' boolean negations (e.g. no_deploy = true -> deploy = false).
    Values must be truthy booleans; we don't support 'no_* = false' (ambiguous).
    """
    out = dict(d)
    for k in list(d.keys()):
        if isinstance(k, str) and k.startswith("no_"):
            base = k[3:]
            val = d[k]
            if not isinstance(val, bool):
                raise ValueError(f"Expected boolean for {k}, got {type(val).__name__}")
            if val:
                out[base] = False
            out.pop(k, None)
    return out


def _ensure_known_keys(scope: str, data: Dict[str, Any], allowed: Set[str]) -> None:
    """Raise if data contains keys not in allowed."""
    unknown = sorted(k for k in data.keys() if k not in allowed)
    if unknown:
        raise ValueError(f"Unknown keys in {scope}: {unknown}")


def _expand_patterns(
    patterns: Iterable[str], base_dir: Path, must_exist: bool = True
) -> Tuple[Path, ...]:
    """
    Expand ?, * and normal paths relative to base_dir (unless absolute).
    Return absolute, deduplicated, sorted paths. Raise if a pattern
    resolves to nothing.

    This helper is used for generic file lists. It intentionally allows
    files to live outside the project directory (for example the
    common_deploy_* lists that are only used on the host).
    """
    results: Set[Path] = set()
    for raw in patterns:
        if not isinstance(raw, str):
            raise ValueError(f"File pattern must be a string, got {type(raw).__name__}")
        raw = raw.strip()
        if not raw:
            raise ValueError("Empty file pattern in configuration")

        is_abs = os.path.isabs(raw)
        pattern_path = Path(raw) if is_abs else (base_dir / raw)
        pattern_str = str(pattern_path)

        if _WILDCARD_RE.search(raw):
            matches = glob.glob(pattern_str, recursive=True)
            if must_exist and not matches:
                raise FileNotFoundError(
                    f"Pattern matched no files: {raw!r} (resolved from {pattern_str})"
                )
            for m in matches:
                p = Path(m).resolve()
                if must_exist and not p.is_file():
                    raise FileNotFoundError(f"Pattern includes non-file: {m!r}")
                results.add(p)
        else:
            p = pattern_path.resolve()
            if must_exist and not p.is_file():
                raise FileNotFoundError(f"File not found: {raw!r} (resolved to {p})")
            results.add(p)

    return tuple(sorted(results))


def _normalize_songbook_path(path: Path, *, project_root: Path) -> Path:
    """Validate a songbook path against the project root.

    Rules:
      - The *path itself* must live inside project_root.
      - The resolved target must also live inside project_root, *unless*
        the path is a symlink inside project_root that points elsewhere.

    In the allowed symlink case we keep the symlink path so that its
    location can later be inspected (for container bind-mounts).
    """
    if not path.is_absolute():
        path = path.absolute()

    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"Songbook file not found: {path}")

    # 1) The configured path itself must be inside the project directory.
    try:
        path.relative_to(project_root)
    except ValueError as exc:  # pragma: no cover - simple guard
        raise ValueError(
            f"Songbook path {path} is outside the project directory {project_root}. "
            "Main document files must reside inside the project directory. "
            "If the actual file lives elsewhere, create a symlink to it inside "
            "the project directory and reference that symlink instead."
        ) from exc

    # 2) The resolved target may be outside the project directory only when
    #    the configured path is a symlink in the project tree.
    target = path.resolve()
    try:
        target.relative_to(project_root)
    except ValueError:
        if not path.is_symlink():
            raise ValueError(
                f"Songbook file {target} is outside the project directory {project_root}. "
                "Direct references to files outside the project directory are not allowed. "
                "Use a symlink inside the project directory instead."
            ) from None

    return path


def _expand_songbook_patterns(
    patterns: Iterable[str], *, config_dir: Path, project_root: Path
) -> Tuple[Path, ...]:
    """Expand and validate songbook patterns.

    This behaves like _expand_patterns() but enforces that main document files stay within the
    project directory, with a single exception: a songbook may be a symlink *inside* the project
    directory that points to a file elsewhere.
    """
    results: Set[Path] = set()

    for raw in patterns:
        if not isinstance(raw, str):
            raise ValueError(f"File pattern must be a string, got {type(raw).__name__}")
        raw_stripped = raw.strip()
        if not raw_stripped:
            raise ValueError("Empty file pattern in configuration")

        is_abs = os.path.isabs(raw_stripped)
        pattern_path = Path(raw_stripped) if is_abs else (config_dir / raw_stripped)
        pattern_str = str(pattern_path)

        if _WILDCARD_RE.search(raw_stripped):
            matches = glob.glob(pattern_str, recursive=True)
            if not matches:
                raise FileNotFoundError(
                    f"Pattern matched no files: {raw!r} (resolved from {pattern_str})"
                )
        else:
            matches = [pattern_str]

        for m in matches:
            p = Path(m)
            # Do *not* resolve here: we want to keep possible symlinks so that
            # we can later detect them when setting up container mounts.
            p = p if p.is_absolute() else (config_dir / p).absolute()
            validated = _normalize_songbook_path(p, project_root=project_root)
            results.add(validated)

    return tuple(sorted(results))


def _resolve_single_file_setting(
    raw: Any,
    *,
    base_dir: Path,
    must_exist: bool = True,
    allow_absolute: bool = False,
) -> Path:
    """
    Resolve a single file setting relative to base_dir.

    - raw must be a non-empty string
    - absolute paths are disallowed by default (allow_absolute=False)
    - wildcards are not allowed
    - returns an absolute Path
    - validates existence if must_exist=True
    """
    if not isinstance(raw, str):
        raise ValueError("Expected a string for single-file setting")
    s = raw.strip()
    if not s:
        raise ValueError("Single-file setting cannot be empty")
    if os.path.isabs(s) and not allow_absolute:
        raise ValueError("Absolute paths are not allowed for this setting")
    if _WILDCARD_RE.search(s):
        raise ValueError("Wildcards are not allowed for this setting")
    p = (base_dir / s) if not os.path.isabs(s) else Path(s)
    p = p.resolve()
    if must_exist and not p.is_file():
        raise FileNotFoundError(f"File not found: {raw!r} (resolved to {p})")
    return p


def _resolve_dir_setting(
    raw: Any,
    *,
    base_dir: Path,
    must_exist: bool = True,
    name: str = "directory",
) -> Path:
    """Resolve a directory path relative to base_dir.

    - raw must be a non-empty string
    - wildcards are not allowed
    - relative paths are resolved against base_dir
    - when must_exist=True, the path must exist and be a directory
    """
    if not isinstance(raw, str):
        raise ValueError(f"Expected a string for {name} path")
    s = raw.strip()
    if not s:
        raise ValueError(f"{name} path cannot be empty")
    if _WILDCARD_RE.search(s):
        raise ValueError(f"Wildcards are not allowed for {name}")
    p = Path(s)
    if not p.is_absolute():
        p = base_dir / p
    p = p.resolve()
    if must_exist:
        if not p.exists():
            raise FileNotFoundError(f"{name} directory not found: {p}")
        if not p.is_dir():
            raise NotADirectoryError(f"{name} path is not a directory: {p}")
    return p


def _parse_modified_cover_png_rules(raw: Any) -> Tuple[ModifiedCoverPngRule, ...]:
    """Validate and normalize modified_cover_png entries from TOML.

    Expects an array of tables. Each entry must provide:
      - width_multiplier (float, >= 0; 0 means "square", width = height)
      - songbook_filenames (optional glob for filenames only, default "*")
      - color (optional ImageMagick color name, default "white")
      - paint_area_rects / paint_area_rect (optional): each rect is
        [x1, y1, x2, y2] with 0.0 <= x1 < x2 <= 1.0 and 0.0 <= y1 < y2 <= 1.0,
        expressed using a bottom-left origin.

    Both dashed and snake_case keys are accepted via _normalize_keys().
    """
    if raw is None:
        return tuple()
    if not isinstance(raw, (list, tuple)):
        raise ValueError("modified-cover-png must be an array of tables/objects")

    rules: list[ModifiedCoverPngRule] = []
    for item in raw:
        if not isinstance(item, dict):
            raise ValueError("Each modified-cover-png entry must be a table/object")
        data = _normalize_keys(item)

        if "width_multiplier" not in data:
            raise ValueError("modified-cover-png entry is missing required 'width-multiplier'")
        try:
            width_multiplier = float(data["width_multiplier"])
        except Exception:
            raise ValueError("width-multiplier must be a number") from None
        if width_multiplier < 0:
            raise ValueError("width-multiplier must be >= 0")

        pattern = data.get("songbook_filenames", "*")
        if not isinstance(pattern, str) or not pattern.strip():
            raise ValueError("songbook-filenames must be a non-empty string")
        if "/" in pattern or "\\" in pattern:
            raise ValueError(
                "songbook-filenames must not contain path separators; only filenames are allowed"
            )

        color = data.get("color", "white")
        if not isinstance(color, str) or not color.strip():
            raise ValueError("color must be a non-empty string")

        rects_raw = []
        if "paint_area_rect" in data and "paint_area_rects" in data:
            raise ValueError("Use either 'paint-area-rect' or 'paint-area-rects', not both")
        if "paint_area_rects" in data:
            rects_raw = data["paint_area_rects"]
        elif "paint_area_rect" in data:
            rects_raw = [data["paint_area_rect"]]

        rects: list[ModifiedCoverPaintRect] = []
        for r in rects_raw or []:
            if not isinstance(r, (list, tuple)) or len(r) != 4:
                raise ValueError(
                    "paint-area-rect(s) must be arrays of four numbers: [x1, y1, x2, y2]"
                )
            x1, y1, x2, y2 = r
            try:
                fx1 = float(x1)
                fy1 = float(y1)
                fx2 = float(x2)
                fy2 = float(y2)
            except Exception:
                raise ValueError("paint-area-rect coordinates must be numbers") from None
            for val in (fx1, fy1, fx2, fy2):
                if not (0.0 <= val <= 1.0):
                    raise ValueError("paint-area-rect coordinates must be between 0.0 and 1.0")
            if not (fx1 < fx2 and fy1 < fy2):
                raise ValueError("paint-area-rect must have x1 < x2 and y1 < y2")
            rects.append(ModifiedCoverPaintRect(x1=fx1, y1=fy1, x2=fx2, y2=fy2))

        rules.append(
            ModifiedCoverPngRule(
                width_multiplier=width_multiplier,
                songbook_filenames=pattern.strip(),
                color=color.strip(),
                paint_area_rects=tuple(rects),
            )
        )

    return tuple(rules)


# TOML loading and profiles
# =========================

_ALLOWED_FILE_KEYS: Set[str] = {
    # Execution
    "sequential",
    "clean_temp",
    "keep_temp",
    "shell",
    "pull",
    # Deploy modes and features (and their negations via _apply_negations)
    "deploy",
    "deploy_last",
    "deploy_common",
    "create_printouts",
    "coverimage",
    "json",
    "midifiles",
    "audiofiles",
    "fast_audio_encode",
    "midifiles_allow_for_optional_variants",
    "audiofiles_allow_for_optional_variants",
    "extrainstrumentbooks",
    "lyricbooks",
    # Files
    "songbooks",
    "common_deploy_icons",
    "common_deploy_metadata",
    "common_deploy_other",
    "deploy_dir",
    # Single-file settings
    "mididir_readme_file",
    "audiodir_readme_file",
    # Cover image tuning
    "cover_image_height",
    "modified_cover_png",
    # Miscellaneous:
    "max_log_lines",
    "verbose",
    # Profile mechanics
    "inherit_from",
    "merge_keys",
}


def _load_toml(path: Path) -> Dict[str, Any]:
    """Load a TOML file and return a dict; raise if missing or not a file."""
    if not path.exists():
        raise FileNotFoundError(f"Configuration file not found: {path}")
    if not path.is_file():
        raise FileNotFoundError(f"Configuration path is not a file: {path}")
    with path.open("rb") as f:
        raw = tomllib.load(f)
    return raw or {}


def _split_flat_and_profiles(
    raw: Dict[str, Any],
) -> Tuple[Dict[str, Any], Dict[str, Dict[str, Any]]]:
    """Split root config and 'profiles' table; normalize keys in both."""
    norm = _normalize_keys(raw)
    profiles = norm.get("profiles")
    flat = {k: v for k, v in norm.items() if k != "profiles"}
    if profiles is None:
        return flat, {}
    if not isinstance(profiles, dict):
        raise ValueError("'profiles' must be a table/object")
    # normalize each profile dict
    profs: Dict[str, Dict[str, Any]] = {}
    for name, content in profiles.items():
        if not isinstance(name, str) or not isinstance(content, dict):
            raise ValueError("Each profile must be a table with a string name")
        profs[name] = _normalize_keys(content)
    return flat, profs


def _resolve_profile_data(
    *,
    profile: str,
    flat: Dict[str, Any],
    profiles: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Build the effective per-profile dict, treating 'flat' as the root/base of
    the inheritance tree:
      flat -> ancestor profiles (if any) -> this profile

    Array merge semantics are controlled by each child profile's merge-keys.
    """
    if not profiles:
        # If no profiles at all, pretend there's an empty 'default'
        profiles = {"default": {}}

    if "default" not in profiles:
        # Create a default profile (empty)
        profiles = dict(profiles)
        profiles["default"] = {}

    seen: Set[str] = set()

    def rec(name: str) -> Dict[str, Any]:
        if name in seen:
            raise ValueError(f"Inheritance cycle detected at profile '{name}'")
        if name not in profiles:
            # Only 'default' is implicitly allowed/created; all others must exist
            raise ValueError(f"Profile '{name}' not found in configuration")
        seen.add(name)
        data = dict(profiles[name])
        parent = data.pop("inherit_from", None)
        # Per-profile merge policy: a list of keys whose array values should be merged
        merge_keys_raw = data.pop("merge_keys", None)
        merge_keys_set: Set[str] = set()
        if merge_keys_raw is not None:
            if not isinstance(merge_keys_raw, (list, tuple)):
                raise ValueError(f"merge-keys must be an array of strings in profile '{name}'")
            for mk in merge_keys_raw:
                if not isinstance(mk, str):
                    raise ValueError(f"merge-keys must be an array of strings in profile '{name}'")
                # Allow authors to use dashed names; normalize to snake_case for matching
                merge_keys_set.add(mk.replace("-", "_"))
        if parent:
            if not isinstance(parent, str):
                raise ValueError(f"inherit-from must be a string in profile '{name}'")
            base = rec(parent)
        else:
            base = dict(flat)
        return _deep_merge_with_array_concat(base, data, merge_keys_set)

    eff = rec(profile)
    return eff


# Build config
# ============


def build_config(
    *,
    args_ns: Any | None,
    config_path: str | Path,
    profile: str = "default",
    env: Mapping[str, str] = os.environ,
    runtime_project_paths: ProjectPaths,
    runtime_in_container: bool,
    runtime_unique_id: str,
    ui: UI | None = None,
) -> Config:
    """
    Build a validated Config by merging defaults, file, profiles, env, and
    CLI args (in that order). Applies quick-mode tweaks last.

    - Resolves file patterns relative to config_dir; validates existence.
    - CLI files, if given, override selection and must exist.
    """
    cfg_path = Path(config_path).resolve()
    raw = _load_toml(cfg_path)
    flat_raw, profiles_raw = _split_flat_and_profiles(raw)

    # Apply negations and validate keys scope-by-scope
    flat = _apply_negations(flat_raw)
    _ensure_known_keys("flat config", flat, _ALLOWED_FILE_KEYS)

    prof_eff = _resolve_profile_data(profile=profile, flat=flat, profiles=profiles_raw)
    prof_eff = _apply_negations(prof_eff)
    _ensure_known_keys(f"profile '{profile}'", prof_eff, _ALLOWED_FILE_KEYS)

    project_root = Path(runtime_project_paths.project_root)

    # Start from defaults
    conf = Config(
        profile=profile,
        config_path=cfg_path,
        config_dir=cfg_path.parent,
        deploy_dir=project_root / DEPLOY_DIRNAME,
    )

    # Merge: defaults -> file (effective profile already includes flat and parents)
    file_over: Dict[str, Any] = dict(prof_eff)

    # Complex/structured settings that exist only in the config file
    if "modified_cover_png" in file_over:
        file_over["modified_cover_png"] = _parse_modified_cover_png_rules(
            file_over["modified_cover_png"]
        )

    # Normalize special booleans/aliases from file
    if "keep_temp" in file_over and "clean_temp" not in file_over:
        val = file_over.pop("keep_temp")
        if not isinstance(val, bool):
            raise ValueError("keep-temp must be a boolean")
        file_over["clean_temp"] = not val
    if "sequential" in file_over:
        val = file_over.pop("sequential")
        if not isinstance(val, bool):
            raise ValueError("sequential must be a boolean")
        # Apply after we know max_parallel, but record intent here
        file_over["_sequential_flag"] = val

    # Environment overrides (simple scalars only; concurrency/memory handled separately below)
    env_max_parallel = _to_int_env(env.get("ULSBS_MAX_PARALLEL"))
    env_container_mem_gb = _to_int_env(env.get("ULSBS_MAX_CONTAINER_MEM_GB"))

    env_over = {
        "use_system_tmp": _to_bool_env(env.get("ULSBS_USE_SYSTEM_TMP_FOR_TEMP")),
        "container_engine": env.get("ULSBS_CONTAINER_ENGINE"),
        "verbose": _to_bool_env(env.get("ULSBS_VERBOSE")),
    }
    env_over = {k: v for k, v in env_over.items() if v is not None}

    # CLI overrides (if provided)
    cli_over: Dict[str, Any] = {}
    cli_files: Iterable[str] = ()
    cli_max_parallel: int | None = None
    if args_ns is not None:
        # Execution/runtime
        if getattr(args_ns, "no_container", False):
            cli_over["use_container"] = False
        if engine := getattr(args_ns, "container_engine", None):
            cli_over["container_engine"] = engine
        if getattr(args_ns, "container_rebuild", False):
            cli_over["container_rebuild"] = True
        if getattr(args_ns, "shell", False):
            cli_over["shell"] = True
        if getattr(args_ns, "pull", False):
            cli_over["pull"] = True
        if getattr(args_ns, "keep_temp", False):
            cli_over["clean_temp"] = False
        if getattr(args_ns, "sequential", False):
            cli_over["_sequential_flag"] = True  # internal flag; applied later

        # Explicit max_parallel from CLI (0 means "auto")
        mp_val = int(getattr(args_ns, "max_parallel", 0) or 0)
        if mp_val > 0:
            cli_max_parallel = mp_val

        # Modes/features
        if getattr(args_ns, "no_deploy", False):
            cli_over["deploy"] = False
        if getattr(args_ns, "no_printouts", False):
            cli_over["create_printouts"] = False
        if getattr(args_ns, "no_coverimage", False):
            cli_over["coverimage"] = False
        if getattr(args_ns, "no_json", False):
            cli_over["json"] = False
        if getattr(args_ns, "no_midi", False):
            cli_over["midifiles"] = False
        if getattr(args_ns, "no_audio", False):
            cli_over["audiofiles"] = False
        if getattr(args_ns, "midifiles_allow_for_optional_variants", False):
            cli_over["midifiles_allow_for_optional_variants"] = True
        if getattr(args_ns, "audiofiles_allow_for_optional_variants", False):
            cli_over["audiofiles_allow_for_optional_variants"] = True
        if getattr(args_ns, "no_extrainstr", False):
            cli_over["extrainstrumentbooks"] = False
        if getattr(args_ns, "no_lyric", False):
            cli_over["lyricbooks"] = False
        if getattr(args_ns, "quick", False):
            cli_over["quick"] = True
        if getattr(args_ns, "fast_audio_encode", False):
            cli_over["fast_audio_encode"] = True
        if getattr(args_ns, "verbose", False):
            cli_over["verbose"] = True

        # Deploy modes
        if getattr(args_ns, "deploy_last", False):
            cli_over["deploy_last"] = True
        if getattr(args_ns, "deploy_common", False):
            cli_over["deploy_common"] = True
        deploy_dir_cli = getattr(args_ns, "deploy_dir", None)
        if deploy_dir_cli is not None:
            cli_over["deploy_dir"] = deploy_dir_cli

        # Misc numeric overrides
        max_log_lines_cli = getattr(args_ns, "max_log_lines", None)
        if max_log_lines_cli is not None:
            try:
                cli_over["max_log_lines"] = int(max_log_lines_cli)
            except Exception:
                raise ValueError("--max-log-lines must be an integer") from None

        # Files from CLI (explicit docs)
        cli_files = list(getattr(args_ns, "files", []) or ())

    # Combine scalar options first (we'll handle files after)
    combined = {**conf.__dict__, **file_over, **env_over, **cli_over}

    # Remove dataclass-only and runtime keys, keep field names only
    combined = {
        k: v
        for k, v in combined.items()
        if hasattr(conf, k)
        or k
        in {
            "_sequential_flag",
            "songbooks",
            "common_deploy_icons",
            "common_deploy_metadata",
            "common_deploy_other",
        }
    }
    conf = replace(conf, **{k: v for k, v in combined.items() if k != "_sequential_flag"})

    # Apply sequential flag (processed after concurrency/memory heuristics below)
    sequential_flag = bool(combined.get("_sequential_flag", False))

    # Clamp integer ranges for non-concurrency fields
    conf = replace(
        conf,
        max_log_lines=_clamp(conf.max_log_lines, 0, 1000, "max_log_lines"),
        cover_image_height=_clamp(conf.cover_image_height, 1, 10000, "cover_image_height"),
    )

    # Derive container memory + max_parallel from system info, env, and CLI

    sys_info = system_info()

    # Determine available memory in GiB
    if sys_info.free_mem_gb is not None:
        memory_available = float(sys_info.free_mem_gb)
    elif sys_info.total_mem_gb is not None:
        memory_available = float(sys_info.total_mem_gb) - float(ASSUMED_OS_MEM_GB)
    else:
        memory_available = 6.0
    if memory_available <= 0:
        memory_available = 6.0

    explicit_env_parallel = env_max_parallel if env_max_parallel is not None else None
    explicit_cli_parallel = cli_max_parallel
    explicit_parallel = (
        explicit_cli_parallel if explicit_cli_parallel is not None else explicit_env_parallel
    )
    explicit_mem_gb = env_container_mem_gb if env_container_mem_gb is not None else None

    # CPU-based upper bound for workers
    if sys_info.cpu_threads is not None and sys_info.cpu_threads > 1:
        cpu_limit = sys_info.cpu_threads - 1
    else:
        cpu_limit = 32

    used_explicit_parallel = False
    used_explicit_mem = False

    if explicit_parallel is not None and explicit_mem_gb is not None:
        # 1) Both max_parallel and container memory explicitly provided
        max_parallel_val = explicit_parallel
        container_mem_val = float(explicit_mem_gb)
        used_explicit_parallel = True
        used_explicit_mem = True
    elif explicit_parallel is not None and explicit_mem_gb is None:
        # 2) Explicit max_parallel only -> derive memory from assumed per-job usage
        max_parallel_val = explicit_parallel
        container_mem_val = float(math.ceil(max_parallel_val * float(ASSUMED_JOB_MEM_GB)))
        used_explicit_parallel = True
    elif explicit_parallel is None and explicit_mem_gb is not None:
        # 3) Explicit container memory only -> derive max_parallel from memory and CPU
        container_mem_val = float(explicit_mem_gb)
        jobs_by_mem = (
            int(memory_available // float(ASSUMED_JOB_MEM_GB))
            if ASSUMED_JOB_MEM_GB > 0
            else int(memory_available)
        )
        if jobs_by_mem < 1:
            jobs_by_mem = 1
        max_parallel_val = min(jobs_by_mem, cpu_limit)
        used_explicit_mem = True
    else:
        # 4) Neither provided -> automatic defaults from available resources
        container_mem_val = float(memory_available)
        jobs_by_mem = (
            int(memory_available // float(ASSUMED_JOB_MEM_GB))
            if ASSUMED_JOB_MEM_GB > 0
            else int(memory_available)
        )
        if jobs_by_mem < 1:
            jobs_by_mem = 1
        max_parallel_val = min(jobs_by_mem, cpu_limit)

    # Apply sequential override last
    if sequential_flag:
        max_parallel_val = 1

    # Final clamps
    max_parallel_val = _clamp(max_parallel_val, 1, 128, "max_parallel")
    container_mem_gb_int = int(math.ceil(container_mem_val))
    if container_mem_gb_int < 2:
        container_mem_gb_int = 2

    # Warnings when overrides were explicitly provided
    if (
        (used_explicit_parallel or used_explicit_mem)
        and ui is not None
        and not runtime_in_container
    ):
        if container_mem_gb_int >= memory_available:
            if used_explicit_mem and conf.use_container:
                ui.warning_line(
                    f"Configured container memory ({container_mem_gb_int} GiB) is >= estimated available"
                )
            else:
                ui.warning_line(
                    f"Estimated maximum memory use ({container_mem_gb_int} GiB) is >= estimated available"
                )
            ui.space_line(
                f"memory ({memory_available:.1f} GiB). This may cause swapping or OOM kills."
            )
        if sys_info.cpu_threads is not None and max_parallel_val >= sys_info.cpu_threads:
            ui.warning_line(
                f"Configured max_parallel ({max_parallel_val}) is >= available CPU threads ({sys_info.cpu_threads})."
            )
            ui.space_line("This may overload the system.")
        if (
            container_mem_gb_int <= math.ceil(max_parallel_val * ASSUMED_JOB_MEM_GB)
            and conf.use_container
        ):
            if used_explicit_mem:
                ui.warning_line(
                    f"Configured container memory ({container_mem_gb_int} GiB) is too small for {max_parallel_val} threads."
                )

    conf = replace(
        conf,
        max_parallel=max_parallel_val,
        container_memory_gb=container_mem_gb_int,
        container_memory_plus_swap_gb=container_mem_gb_int,
    )

    # Resolve and validate file patterns from config (relative to config_dir)
    cfg_dir = conf.config_dir

    # Resolve deploy directory (may be overridden via config/CLI).
    deploy_dir_explicit = ("deploy_dir" in file_over) or ("deploy_dir" in cli_over)
    if deploy_dir_explicit:
        raw_deploy = combined.get("deploy_dir")
        if not isinstance(raw_deploy, str):
            raise ValueError("deploy_dir must be a string path")
        deploy_dir_path = _resolve_dir_setting(
            raw_deploy,
            base_dir=project_root,
            must_exist=not runtime_in_container,
            name="deploy_dir",
        )
    else:
        deploy_dir_path = project_root / DEPLOY_DIRNAME

    songbooks_cfg: Tuple[Path, ...] = ()
    # Only validate/expand songbooks from config when CLI has not provided
    # explicit songbook files. If CLI files are present, they fully override
    # the config-defined songbooks, and we must *not* force validation of
    # potentially unused config songbooks (for example symlinks that are not
    # even mounted into the container).
    if not cli_files and "songbooks" in file_over:
        if not isinstance(file_over["songbooks"], (list, tuple)):
            raise ValueError("songbooks must be an array")
        songbooks_cfg = _expand_songbook_patterns(
            file_over["songbooks"], config_dir=cfg_dir, project_root=project_root
        )

    # If in a container, the common files don't need to exist, as they might be
    # located outside the mounted project directory, and they are only used
    # for deploying, which happens always on the host only.
    common_must_exist = not runtime_in_container

    common_deploy_icons: Tuple[Path, ...] = ()
    if "common_deploy_icons" in file_over:
        if not isinstance(file_over["common_deploy_icons"], (list, tuple)):
            raise ValueError("common-deploy-icons must be an array")
        common_deploy_icons = _expand_patterns(
            file_over["common_deploy_icons"], cfg_dir, must_exist=common_must_exist
        )

    common_deploy_metadata: Tuple[Path, ...] = ()
    if "common_deploy_metadata" in file_over:
        if not isinstance(file_over["common_deploy_metadata"], (list, tuple)):
            raise ValueError("common-deploy-metadata must be an array")
        common_deploy_metadata = _expand_patterns(
            file_over["common_deploy_metadata"], cfg_dir, must_exist=common_must_exist
        )

    common_deploy_other: Tuple[Path, ...] = ()
    if "common_deploy_other" in file_over:
        if not isinstance(file_over["common_deploy_other"], (list, tuple)):
            raise ValueError("common-deploy-other must be an array")
        common_deploy_other = _expand_patterns(
            file_over["common_deploy_other"], cfg_dir, must_exist=common_must_exist
        )

    # Single-file settings (must exist, relative to config dir, no absolute)
    mididir_readme_file_path: Path | None = None
    if "mididir_readme_file" in file_over:
        mididir_readme_file_path = _resolve_single_file_setting(
            file_over["mididir_readme_file"],
            base_dir=cfg_dir,
            must_exist=True,
            allow_absolute=False,
        )

    audiodir_readme_file_path: Path | None = None
    if "audiodir_readme_file" in file_over:
        audiodir_readme_file_path = _resolve_single_file_setting(
            file_over["audiodir_readme_file"],
            base_dir=cfg_dir,
            must_exist=True,
            allow_absolute=False,
        )

    # CLI explicit files override selection if provided
    selected_songbooks: Tuple[Path, ...] = ()
    if cli_files:
        resolved: Set[Path] = set()
        for raw in cli_files:
            if not isinstance(raw, str) or not raw.strip():
                raise ValueError("CLI file entries must be non-empty strings")
            s = raw.strip()
            p = Path(s)
            if p.is_absolute():
                link_path = p
            else:
                # Always interpret CLI paths as relative to the project root,
                # not to the current working directory.
                link_path = (project_root / p).absolute()
            validated = _normalize_songbook_path(link_path, project_root=project_root)
            resolved.add(validated)
        selected_songbooks = tuple(sorted(resolved))

    # Finalize with resolved files
    conf = replace(
        conf,
        songbooks=(selected_songbooks or songbooks_cfg),
        common_deploy_icons=common_deploy_icons,
        common_deploy_metadata=common_deploy_metadata,
        common_deploy_other=common_deploy_other,
        mididir_readme_file=mididir_readme_file_path,
        audiodir_readme_file=audiodir_readme_file_path,
        deploy_dir=deploy_dir_path,
        runtime=Runtime(
            project_paths=runtime_project_paths,
            in_container=runtime_in_container,
            unique_id=runtime_unique_id,
            system_info=sys_info,
        ),
    )

    # Apply quick-mode derivations last
    if conf.quick:
        conf = replace(
            conf,
            deploy=False,
            create_printouts=False,
            coverimage=False,
            clean_temp=False,
            extrainstrumentbooks=False,
            lyricbooks=False,
            midifiles=False,
            audiofiles=False,
        )

    # store globally
    global _last_built_config
    _last_built_config = conf

    return conf
