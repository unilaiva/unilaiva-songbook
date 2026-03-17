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
import tomllib
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Tuple, Set

from .constants import CONFIG_FILENAME, COVERIMAGE_HEIGHT


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

    # Features
    extrainstrumentbooks: bool = True
    lyricbooks: bool = True
    create_printouts: bool = True
    coverimage: bool = True
    midifiles: bool = True
    audiofiles: bool = True
    midifiles_allow_for_optional_variants: bool = False
    audiofiles_allow_for_optional_variants: bool = False
    fast_audio_encode: bool = False

    # Docker resources
    container_memory: str = "6g"
    container_memory_plus_swap: str = "6g"

    # Files (absolute paths, validated to exist)
    songbooks: Tuple[Path, ...] = field(default_factory=tuple) # From config, possibly overwritten by CLI
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
        raise ValueError(f"{nm} must be an integer, got {type(v).__name__}")
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


def _expand_patterns(patterns: Iterable[str], base_dir: Path, must_exist: bool = True) -> Tuple[Path, ...]:
    """
    Expand ?, * and normal paths relative to base_dir (unless absolute).
    Return absolute, deduplicated, sorted paths. Raise if a pattern
    resolves to nothing.
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
                raise FileNotFoundError(f"Pattern matched no files: {raw!r} (resolved from {pattern_str})")
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
    for idx, item in enumerate(raw):
        if not isinstance(item, dict):
            raise ValueError("Each modified-cover-png entry must be a table/object")
        data = _normalize_keys(item)

        if "width_multiplier" not in data:
            raise ValueError("modified-cover-png entry is missing required 'width-multiplier'")
        try:
            width_multiplier = float(data["width_multiplier"])
        except Exception:
            raise ValueError("width-multiplier must be a number")
        if width_multiplier < 0:
            raise ValueError("width-multiplier must be >= 0")

        pattern = data.get("songbook_filenames", "*")
        if not isinstance(pattern, str) or not pattern.strip():
            raise ValueError("songbook-filenames must be a non-empty string")
        if "/" in pattern or "\\" in pattern:
            raise ValueError("songbook-filenames must not contain path separators; only filenames are allowed")

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
                raise ValueError("paint-area-rect(s) must be arrays of four numbers: [x1, y1, x2, y2]")
            x1, y1, x2, y2 = r
            try:
                fx1 = float(x1)
                fy1 = float(y1)
                fx2 = float(x2)
                fy2 = float(y2)
            except Exception:
                raise ValueError("paint-area-rect coordinates must be numbers")
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
    "use_container", "container_rebuild", "container_engine", "container",
    "max_parallel", "sequential", "use_system_tmp", "clean_temp", "keep_temp",
    "shell", "pull",
    # Deploy modes and features (and their negations via _apply_negations)
    "deploy", "deploy_last", "deploy_common", "create_printouts", "coverimage",
    "midifiles", "audiofiles", "fast_audio_encode",
    "midifiles_allow_for_optional_variants", "audiofiles_allow_for_optional_variants",
    "extrainstrumentbooks", "lyricbooks", "quick",
    # Container resources
    "container_memory", "container_memory_plus_swap",
    # Files
    "songbooks", "common_deploy_icons", "common_deploy_metadata", "common_deploy_other",
    # Single-file settings
    "mididir_readme_file", "audiodir_readme_file",
    # Cover image tuning
    "cover_image_height", "modified_cover_png",
    # Miscellaneous:
    "max_log_lines", "verbose",
    # Profile mechanics
    "inherit_from", "merge_keys",
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


def _split_flat_and_profiles(raw: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Dict[str, Any]]]:
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

    # Start from defaults
    conf = Config(profile=profile, config_path=cfg_path, config_dir=cfg_path.parent)

    # Merge: defaults -> file (effective profile already includes flat and parents)
    file_over: Dict[str, Any] = dict(prof_eff)

    # Complex/structured settings that exist only in the config file
    if "modified_cover_png" in file_over:
        file_over["modified_cover_png"] = _parse_modified_cover_png_rules(file_over["modified_cover_png"])

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

    # Environment overrides
    env_over = {
        "use_system_tmp": _to_bool_env(env.get("ULSBS_USE_SYSTEM_TMP_FOR_TEMP")),
        "container_engine": env.get("ULSBS_CONTAINER_ENGINE"),
        "container_memory": env.get("ULSBS_MAX_CONTAINER_MEMORY"),
        "container_memory_plus_swap": env.get("ULSBS_MAX_CONTAINER_MEMORY"),
        "max_parallel": _to_int_env(env.get("ULSBS_MAX_PARALLEL")),
        "verbose": _to_bool_env(env.get("ULSBS_VERBOSE")),
    }
    env_over = {k: v for k, v in env_over.items() if v is not None}

    # CLI overrides (if provided)
    cli_over: Dict[str, Any] = {}
    cli_files: Iterable[str] = ()
    if args_ns is not None:
        # Execution/runtime
        cli_over["use_container"] = not bool(getattr(args_ns, "no_container", False))
        if getattr(args_ns, "container_engine", None):
            cli_over["container_engine"] = getattr(args_ns, "container_engine")
        cli_over["container_rebuild"] = bool(getattr(args_ns, "container_rebuild", False))
        cli_over["shell"] = bool(getattr(args_ns, "shell", False))
        cli_over["pull"] = bool(getattr(args_ns, "pull", False))
        cli_over["clean_temp"] = not bool(getattr(args_ns, "keep_temp", False))
        if bool(getattr(args_ns, "sequential", False)):
            cli_over["_sequential_flag"] = True  # internal flag; applied later

        # Modes/features
        cli_over["deploy"] = not bool(getattr(args_ns, "no_deploy", False))
        cli_over["create_printouts"] = not bool(getattr(args_ns, "no_printouts", False))
        cli_over["coverimage"] = not bool(getattr(args_ns, "no_coverimage", False))
        cli_over["midifiles"] = not bool(getattr(args_ns, "no_midi", False))
        cli_over["audiofiles"] = not bool(getattr(args_ns, "no_audio", False))
        cli_over["midifiles_allow_for_optional_variants"] = bool(getattr(args_ns, "midifiles_allow_for_optional_variants", False))
        cli_over["audiofiles_allow_for_optional_variants"] = bool(getattr(args_ns, "audiofiles_allow_for_optional_variants", False))
        cli_over["extrainstrumentbooks"] = not bool(getattr(args_ns, "no_extrainstr", False))
        cli_over["lyricbooks"] = not bool(getattr(args_ns, "no_lyric", False))
        cli_over["quick"] = bool(getattr(args_ns, "q", False))
        cli_over["fast_audio_encode"] = bool(getattr(args_ns, "fast_audio_encode", False))
        cli_over["verbose"] = bool(getattr(args_ns, "verbose", False))

        # Deploy modes
        cli_over["deploy_last"] = bool(getattr(args_ns, "deploy_last", False))
        cli_over["deploy_common"] = bool(getattr(args_ns, "deploy_common", False))

        # Misc numeric overrides
        max_log_lines_cli = getattr(args_ns, "max_log_lines", None)
        if max_log_lines_cli is not None:
            try:
                cli_over["max_log_lines"] = int(max_log_lines_cli)
            except Exception:
                raise ValueError("--max-log-lines must be an integer")

        # Files from CLI (explicit docs)
        cli_files = list(getattr(args_ns, "files", []) or ())

    # Combine scalar options first (we'll handle files after)
    combined = {**conf.__dict__, **file_over, **env_over, **cli_over}

    # Allow 'container' (from no-container negation) as an alias for use_container
    if "container" in combined and "use_container" not in combined:
        combined["use_container"] = bool(combined["container"])
    combined.pop("container", None)
    # Remove dataclass-only and runtime keys, keep field names only
    combined = {k: v for k, v in combined.items() if hasattr(conf, k) or k in {"_sequential_flag", "songbooks", "common_deploy_icons", "common_deploy_metadata", "common_deploy_other"}}
    conf = replace(conf, **{k: v for k, v in combined.items() if k != "_sequential_flag"})

    # Apply sequential flag to max_parallel if set anywhere
    sequential_flag = bool(combined.get("_sequential_flag", False))
    if sequential_flag:
        conf = replace(conf, max_parallel=1)

    # Clamp integer ranges
    conf = replace(
        conf,
        max_parallel=_clamp(conf.max_parallel, 1, 64, "max_parallel"),
        max_log_lines=_clamp(conf.max_log_lines, 0, 1000, "max_log_lines"),
        cover_image_height=_clamp(conf.cover_image_height, 1, 10000, "cover_image_height"),
    )

    # Resolve and validate file patterns from config (relative to config_dir)
    cfg_dir = conf.config_dir
    songbooks_cfg: Tuple[Path, ...] = ()
    if "songbooks" in file_over:
        if not isinstance(file_over["songbooks"], (list, tuple)):
            raise ValueError("songbooks must be an array")
        songbooks_cfg = _expand_patterns(file_over["songbooks"], cfg_dir, must_exist=True)

    # If in a container, the common files don't need to exist, as they might be
    # located outside the mounted project directory, and they are only used
    # for deploying, which happens always on the host only.
    common_must_exist = not runtime_in_container

    common_deploy_icons: Tuple[Path, ...] = ()
    if "common_deploy_icons" in file_over:
        if not isinstance(file_over["common_deploy_icons"], (list, tuple)):
            raise ValueError("common-deploy-icons must be an array")
        common_deploy_icons = _expand_patterns(file_over["common_deploy_icons"], cfg_dir, must_exist=common_must_exist)

    common_deploy_metadata: Tuple[Path, ...] = ()
    if "common_deploy_metadata" in file_over:
        if not isinstance(file_over["common_deploy_metadata"], (list, tuple)):
            raise ValueError("common-deploy-metadata must be an array")
        common_deploy_metadata = _expand_patterns(file_over["common_deploy_metadata"], cfg_dir, must_exist=common_must_exist)

    common_deploy_other: Tuple[Path, ...] = ()
    if "common_deploy_other" in file_over:
        if not isinstance(file_over["common_deploy_other"], (list, tuple)):
            raise ValueError("common-deploy-other must be an array")
        common_deploy_other = _expand_patterns(file_over["common_deploy_other"], cfg_dir, must_exist=common_must_exist)

    # Single-file settings (must exist, relative to config dir, no absolute)
    mididir_readme_file_path: Path | None = None
    if "mididir_readme_file" in file_over:
        mididir_readme_file_path = _resolve_single_file_setting(
            file_over["mididir_readme_file"], base_dir=cfg_dir, must_exist=True, allow_absolute=False
        )

    audiodir_readme_file_path: Path | None = None
    if "audiodir_readme_file" in file_over:
        audiodir_readme_file_path = _resolve_single_file_setting(
            file_over["audiodir_readme_file"], base_dir=cfg_dir, must_exist=True, allow_absolute=False
        )

    # CLI explicit files override selection if provided
    selected_songbooks: Tuple[Path, ...] = ()
    if cli_files:
        resolved: Set[Path] = set()
        for raw in cli_files:
            if not isinstance(raw, str) or not raw.strip():
                raise ValueError("CLI file entries must be non-empty strings")
            p = Path(raw)
            if not p.is_absolute() and not p.is_file():
                # Resolve relative to the project root
                p = (Path(getattr(runtime_project_paths, "project_root")) / p).resolve()
            else:
                p = p.resolve()
            if not p.is_file():
                raise FileNotFoundError(f"CLI file not found: {raw!r} (resolved to {p})")
            resolved.add(p)
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
        runtime=Runtime(
            project_paths=runtime_project_paths,
            in_container=runtime_in_container,
            unique_id=runtime_unique_id,
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
