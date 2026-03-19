#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2016-2026 Lari Natri <lari.natri@iki.fi>
# SPDX-License-Identifier: GPL-3.0-or-later

"""
Render MIDI files to audio using FluidSynth and FFmpeg.

Key features:

- Uses only the Python standard library plus external fluidsynth and
  ffmpeg binaries (and optionally metaflac) available in PATH.
- Pipes FluidSynth into FFmpeg for both loudness analysis and encoding.
  All requested output formats are produced in a single fluidsynth -> ffmpeg
  run: a filter_complex with asplit fans the decoded audio out to per-format
  chains (loudnorm -> alimiter -> optional aresample), with one -map block per
  output file. By default uses EBU R128 loudnorm (optionally two-pass) and an
  optional true-peak limiter; loudnorm can be disabled with -L 0 for faster
  encoding.
- Supports MP3 / FLAC / WAV outputs and basic metadata tagging, including
  optional embedded cover images for MP3 and FLAC.
- Sensible configurable defaults

This file is part of the ULSBS package, but does not depend on any of it's
components and can be used by itself.

This module is the implementation behind the ulsbs-midi2audio command.
It can also be run directly as:

    python3 -m ulsbs.tools.midi2audio input.mid
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

# Test for python version before importing any package modules.
REQUIRED = (3, 11)
if sys.version_info < REQUIRED:
    sys.stderr.write(
        "This script requires Python {}.{}+, but you are running {}.{}.{}\n".format(
            REQUIRED[0], REQUIRED[1], *sys.version_info[:3]
        )
    )
    raise SystemExit(1)


# Defaults and configuration
# ==========================


SF2_CANDIDATES: Tuple[Path, ...] = (
    Path("/usr/share/sounds/sf2/FluidR3_GM.sf2"),
    Path("/usr/share/soundfonts/FluidR3_GM.sf2"),
    Path("/usr/share/sounds/sf2/FluidR3_GS.sf2"),
    Path("/usr/share/soundfonts/FluidR3_GS.sf2"),
    Path("/usr/share/sounds/sf2/default.sf2"),
    Path("/usr/share/soundfonts/default.sf2"),
)


@dataclass
class Options:
    # Output selection
    want_mp3: bool = False
    want_flac: bool = False
    want_wav: bool = False
    want_raw: bool = False

    out_base: Path | None = None  # -o
    force: bool = False  # -y

    # Rendering / sound
    sf2: Path | None = None
    rate: int = 48_000
    gain: float = 0.60

    # Reverb
    rev_active: bool = True
    rev_room: float = 0.60
    rev_damp: float = 0.30
    rev_level: float = 0.60
    rev_width: float = 0.90

    # Chorus
    chorus_active: bool = False
    chorus_lines: int = 3
    chorus_level: float = 0.60
    chorus_speed: float = 0.20
    chorus_depth: float = 4.25

    # Loudness (loudnorm)
    enable_loudnorm: bool = True
    lufs: float = -14.0
    lra: float = 7.0
    tp: float = -0.10
    two_pass: bool = False

    # Limiter
    clip_guard: bool = False
    guard_tp: float = 0.9
    lim_attack: float = 5.0
    lim_release: float = 50.0

    # MP3
    vbr_q: int = 2
    cbr_kbps: int | None = None

    # Bit depths
    flac_bits: int = 24
    wav_bits: int = 24

    # Behaviour
    threads: int = 0
    verbose: bool = False
    quiet: bool = False
    dry_run: bool = False

    # Tagging (subset; mirrored from midi2audio.sh for MP3/FLAC)
    tag_title: str | None = None
    tag_artist: str | None = None
    tag_tracknr: str | None = None
    tag_album: str | None = None
    tag_albumartist: str | None = None
    tag_year: str | None = None
    tag_image: Path | None = None


# HELPERS
# =======


class Midi2AudioError(RuntimeError):
    """Local exception for user-visible errors."""


def _which(prog: str) -> str | None:
    return shutil.which(prog)


def _check_deps() -> None:
    if not _which("fluidsynth"):
        raise Midi2AudioError("'fluidsynth' binary not found in PATH")
    if not _which("ffmpeg"):
        raise Midi2AudioError("'ffmpeg' binary not found in PATH")


def _float_in_range(val: float, lo: float, hi: float, name: str) -> None:
    if not (lo <= val <= hi):
        raise Midi2AudioError(f"{name} must be between {lo} and {hi} (got {val})")


def _find_soundfont(explicit: Path | None) -> Path:
    if explicit is not None:
        if explicit.is_file():
            return explicit
        raise Midi2AudioError(f"SoundFont not found: {explicit}")

    # Env var SF2_FILE first
    env_sf = os.environ.get("SF2_FILE")
    if env_sf:
        p = Path(env_sf)
        if p.is_file():
            return p

    # Fallbacks
    for cand in SF2_CANDIDATES:
        if cand.is_file():
            return cand
    raise Midi2AudioError(
        "SoundFont file not found in default locations; specify one with -s"
    )


def _strip_audio_ext(path: Path) -> Path:
    if path.suffix.lower() in {".mp3", ".flac", ".wav"}:
        return path.with_suffix("")
    return path


def _confirm_overwrite(path: Path, opts: Options) -> bool:
    """Ask user before overwriting an existing file, unless forced.

    Returns True if overwrite is allowed.
    """

    if not path.exists() or opts.force or opts.dry_run:
        return True
    try:
        ans = input(f"File exists: {path} - overwrite? [y/N] ").strip().lower()
    except EOFError:
        return False
    return ans == "y"


def _ffmpeg_base_args(opts: Options, *, overwrite: bool, loglevel: str | None = None) -> List[str]:
    if loglevel is None:
        loglevel = "info" if opts.verbose and not opts.quiet else "error"
    args = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        loglevel,
    ]
    if overwrite:
        args.append("-y")
    else:
        args.append("-n")
    if opts.threads >= 0:
        args.extend(["-threads", str(opts.threads)])
    if opts.quiet and not opts.verbose:
        args.append("-nostats")
    return args


def _run(cmd: Sequence[str], *, capture_stderr: bool = False) -> subprocess.CompletedProcess:
    return subprocess.run(
        list(cmd),
        check=True,
        stdout=subprocess.PIPE if capture_stderr else None,
        stderr=subprocess.PIPE if capture_stderr else None,
    )


def _run_verbose(cmd: Sequence[str], opts: Options, *, capture_stderr: bool = False) -> subprocess.CompletedProcess:
    if opts.verbose or opts.dry_run:
        sys.stdout.write("+ " + " ".join(str(c) for c in cmd) + "\n")
        sys.stdout.flush()
    if opts.dry_run:
        # Fake result
        class Dummy:
            returncode = 0
            stdout = b""
            stderr = b""

        return Dummy()  # type: ignore[return-value]
    return _run(cmd, capture_stderr=capture_stderr)


# Shared command builders
# =======================


def _fluidsynth_cmd(midi: Path, opts: Options, sf2: Path) -> List[str]:
    """Build the fluidsynth command for raw f32 stereo output to stdout."""
    fs_rate = min(opts.rate, 96_000)  # Fluidsynth supports max 96000 Hz
    return [
        "fluidsynth",
        "-a",
        "file",
        "-ni",
        "-F",
        "-",
        "-T",
        "raw",
        "-O",
        "float",
        "-r",
        str(fs_rate),
        "-g",
        f"{opts.gain}",
        "-o",
        f"synth.chorus.active={int(opts.chorus_active)}",
        "-o",
        f"synth.chorus.level={opts.chorus_level}",
        "-o",
        f"synth.chorus.nr={opts.chorus_lines}",
        "-o",
        f"synth.chorus.speed={opts.chorus_speed}",
        "-o",
        f"synth.chorus.depth={opts.chorus_depth}",
        "-o",
        f"synth.reverb.active={int(opts.rev_active)}",
        "-o",
        f"synth.reverb.room-size={opts.rev_room}",
        "-o",
        f"synth.reverb.damp={opts.rev_damp}",
        "-o",
        f"synth.reverb.level={opts.rev_level}",
        "-o",
        f"synth.reverb.width={opts.rev_width}",
        str(sf2),
        str(midi),
    ]


def _ffmpeg_rawinput_args(opts: Options) -> List[str]:
    """Return ffmpeg args to read raw f32le stereo from stdin."""
    return [
        "-f",
        "f32le",
        "-ar",
        str(opts.rate),
        "-ac",
        "2",
        "-channel_layout",
        "stereo",
        "-guess_layout_max",
        "0",
        "-i",
        "-",
    ]


def _metadata_args(opts: Options) -> List[str]:
    """Return ffmpeg metadata tag arguments from opts."""
    args: List[str] = []
    if opts.tag_title:
        args += ["-metadata", f"title={opts.tag_title}"]
    if opts.tag_artist:
        args += ["-metadata", f"artist={opts.tag_artist}"]
    if opts.tag_album:
        args += ["-metadata", f"album={opts.tag_album}"]
    if opts.tag_albumartist:
        args += ["-metadata", f"album_artist={opts.tag_albumartist}"]
    if opts.tag_tracknr:
        args += ["-metadata", f"track={opts.tag_tracknr}"]
    if opts.tag_year:
        args += ["-metadata", f"date={opts.tag_year}"]
    return args


def _collect_kinds(opts: Options) -> List[str]:
    """Return the list of output kinds requested by the user."""
    kinds: List[str] = []
    if opts.want_mp3:
        kinds.append("mp3")
    if opts.want_flac:
        kinds.append("flac")
    if opts.want_wav:
        kinds.append("wav")
    if opts.want_raw:
        kinds.append("raw")
    return kinds


def _output_path_for_kind(base: Path, kind: str) -> Path | None:
    """Map an output kind to a file path, or None if unknown."""
    if kind == "raw":
        return base.with_suffix(".RAWRENDER.wav")
    if kind == "mp3":
        return base.with_suffix(".mp3")
    if kind == "flac":
        return base.with_suffix(".flac")
    if kind == "wav":
        return base.with_suffix(".wav")
    return None


# Pipeline
# ========


def _run_pipeline(
    fs_cmd: Sequence[str],
    ff_cmd: Sequence[str],
    opts: Options,
    *,
    capture_ffmpeg_stderr: bool = False,
) -> subprocess.CompletedProcess:
    """Run a fluidsynth -> ffmpeg pipeline.

    fluidsynth writes raw f32 stereo audio to stdout; ffmpeg reads from stdin.
    Returns the CompletedProcess from ffmpeg. Raises Midi2AudioError on errors.
    """

    if opts.verbose or opts.dry_run:
        sys.stdout.write(
            "+ "
            + " ".join(str(x) for x in fs_cmd)
            + " | "
            + " ".join(str(x) for x in ff_cmd)
            + "\n"
        )
        sys.stdout.flush()
    if opts.dry_run:
        class Dummy:
            returncode = 0
            stdout = b""
            stderr = b""

        return Dummy()  # type: ignore[return-value]

    fs_proc = subprocess.Popen(
        list(fs_cmd),
        stdout=subprocess.PIPE,
        stderr=None if opts.verbose else subprocess.DEVNULL,
    )
    try:
        ff_proc = subprocess.run(
            list(ff_cmd),
            stdin=fs_proc.stdout,
            check=True,
            stdout=None,
            stderr=subprocess.PIPE if capture_ffmpeg_stderr else None,
        )
    except subprocess.CalledProcessError as e:
        if fs_proc.stdout is not None:
            fs_proc.stdout.close()
        fs_proc.wait()
        raise Midi2AudioError(
            f"ffmpeg failed with exit code {e.returncode}"
        ) from e
    finally:
        if fs_proc.stdout is not None:
            fs_proc.stdout.close()
        fs_proc.wait()

    return ff_proc


def _analyze_loudness(midi: Path, opts: Options, sf2: Path) -> Dict[str, float]:
    """Run first-pass loudnorm analysis by piping fluidsynth into ffmpeg."""

    fs_cmd = _fluidsynth_cmd(midi, opts, sf2)

    # loglevel must be at least "info" so that loudnorm emits its JSON
    # analysis block to stderr, regardless of the user's verbosity setting.
    ff = _ffmpeg_base_args(opts, overwrite=False, loglevel="info")
    ff += _ffmpeg_rawinput_args(opts)
    ff += [
        "-filter:a",
        f"loudnorm=I={opts.lufs}:LRA={opts.lra}:TP={opts.tp}:print_format=json",
        "-f",
        "null",
        "-",
    ]

    proc = _run_pipeline(fs_cmd, ff, opts, capture_ffmpeg_stderr=True)

    stderr = (proc.stderr or b"").decode("utf-8", errors="replace")
    m = re.search(r"\{.*\}", stderr, flags=re.DOTALL)
    if not m:
        raise Midi2AudioError("ffmpeg loudnorm analysis did not produce JSON output")
    try:
        data = json.loads(m.group(0))
    except json.JSONDecodeError as e:
        raise Midi2AudioError(f"Failed to parse loudnorm JSON: {e}") from None

    required = [
        "input_i",
        "input_lra",
        "input_tp",
        "input_thresh",
        "target_offset",
    ]
    missing = [k for k in required if k not in data]
    if missing:
        raise Midi2AudioError(f"Missing keys from loudnorm analysis: {missing}")

    return {k: float(data[k]) for k in required}


def _build_loudnorm_filter(opts: Options, analysis: Dict[str, float] | None) -> str:
    if not analysis:
        return f"loudnorm=I={opts.lufs}:LRA={opts.lra}:TP={opts.tp}"
    return (
        "loudnorm="
        f"I={opts.lufs}:LRA={opts.lra}:TP={opts.tp}:"
        f"measured_I={analysis['input_i']}:"
        f"measured_LRA={analysis['input_lra']}:"
        f"measured_TP={analysis['input_tp']}:"
        f"measured_thresh={analysis['input_thresh']}:"
        f"offset={analysis['target_offset']}:"
        "linear=true:print_format=summary"
    )


# Per-MIDI processing
# ===================


def _per_kind_filter_chain(kind: str, loudnorm_filter: str | None, opts: Options) -> str | None:
    """Return the filter_complex chain string for one output branch, or None.

    raw always bypasses all filters (returns None). For every other kind,
    the chain is: loudnorm (when present) -> alimiter (when clip_guard is set)
    -> aresample to 48 kHz (MP3 only, when the project rate exceeds 48 kHz).
    Returning None means the split pad maps straight to the output muxer with
    no intervening filter.
    """
    if kind == "raw":
        return None

    parts: List[str] = []
    if loudnorm_filter is not None:
        parts.append(loudnorm_filter)
    if opts.clip_guard:
        parts.append(
            f"alimiter=limit={opts.guard_tp}"
            f":attack={opts.lim_attack}"
            f":release={opts.lim_release}"
        )

    # MP3 encoders only accept 44.1 kHz or 48 kHz
    if kind == "mp3" and opts.rate not in (44_100, 48_000):
        parts.append("aresample=48000")

    return ",".join(parts) if parts else None


def _build_multi_output_ffmpeg(
    kinds: List[str],
    out_paths: Dict[str, Path],
    loudnorm_filter: str | None,
    opts: Options,
) -> List[str]:
    """Return a single ffmpeg command that writes every requested format at once.

    The decoded audio from stdin is fanned out with asplit (one branch per
    output). Each branch gets its own filter chain via filter_complex so that
    loudnorm, the limiter, and any resampling run inside one ffmpeg process.
    For a single output with no filter the filter_complex is omitted entirely
    and the input stream is mapped directly.

    Layout (N > 1 example)::

        [0:a] asplit=N [s0][s1]...[sN-1]
        [s0] loudnorm=...,alimiter=... [mp3_out]
        [s1] loudnorm=...,alimiter=... [flac_out]
        [s2] loudnorm=...,alimiter=... [wav_out]
        [s3]                            <- raw, mapped directly from split pad

    Each output section then follows::

        -map [mp3_out]  <mp3 codec/rate/id3 args>  out.mp3
        -map [flac_out] <flac codec args>          out.flac
        ...
    """
    N = len(kinds)
    filter_parts: List[str] = []
    kind_to_pad: Dict[str, str] = {}  # kind -> pad label (or "0:a" for direct)

    chains: Dict[str, str | None] = {
        k: _per_kind_filter_chain(k, loudnorm_filter, opts) for k in kinds
    }

    if N == 1:
        kind = kinds[0]
        chain = chains[kind]
        if chain:
            pad = f"{kind}_out"
            filter_parts.append(f"[0:a]{chain}[{pad}]")
            kind_to_pad[kind] = pad
        else:
            # No filter at all: skip filter_complex, map raw input directly
            kind_to_pad[kind] = "0:a"
    else:
        split_labels = [f"s{i}" for i in range(N)]
        filter_parts.append(
            f"[0:a]asplit={N}" + "".join(f"[{lbl}]" for lbl in split_labels)
        )
        for i, kind in enumerate(kinds):
            chain = chains[kind]
            if chain:
                pad = f"{kind}_out"
                filter_parts.append(f"[{split_labels[i]}]{chain}[{pad}]")
                kind_to_pad[kind] = pad
            else:
                # raw (or unfiltered output): use split pad directly
                kind_to_pad[kind] = split_labels[i]

    ff = _ffmpeg_base_args(opts, overwrite=True)  # overwrites confirmed upfront
    ff += _ffmpeg_rawinput_args(opts)

    if filter_parts:
        ff += ["-filter_complex", ";".join(filter_parts)]

    meta_args = _metadata_args(opts)

    for kind in kinds:
        pad = kind_to_pad[kind]
        ff += ["-map", "0:a" if pad == "0:a" else f"[{pad}]"]

        out_path = out_paths[kind]

        if kind == "mp3":
            mp3_rate = opts.rate if opts.rate in (44_100, 48_000) else 48_000
            if opts.cbr_kbps is not None:
                ff += ["-c:a", "libmp3lame", "-b:a", f"{opts.cbr_kbps}k"]
            else:
                ff += ["-c:a", "libmp3lame", "-q:a", str(opts.vbr_q)]
            ff += ["-ac", "2", "-ar", str(mp3_rate)]
            ff += ["-id3v2_version", "3", "-write_id3v1", "0"]
            ff += meta_args
            ff.append(str(out_path))

        elif kind == "flac":
            sample_fmt = "s16" if opts.flac_bits == 16 else "s32"
            bits = "16" if opts.flac_bits == 16 else "24"
            ff += [
                "-c:a", "flac",
                "-compression_level", "8",
                "-sample_fmt", sample_fmt,
                "-bits_per_raw_sample", bits,
                "-ac", "2",
                "-ar", str(opts.rate),
            ]
            ff += meta_args
            ff.append(str(out_path))

        elif kind == "wav":
            codec = "pcm_s16le" if opts.wav_bits == 16 else "pcm_s24le"
            ff += ["-c:a", codec, "-ac", "2", "-ar", str(opts.rate)]
            ff += meta_args
            ff.append(str(out_path))

        elif kind == "raw":
            # Pre-filter capture: 24-bit PCM, no loudnorm or limiter
            ff += ["-c:a", "pcm_s24le", "-ac", "2", "-ar", str(opts.rate)]
            ff += meta_args
            ff.append(str(out_path))

        else:
            raise Midi2AudioError(f"Unknown output kind: {kind}")

    return ff


def _attach_cover_art(out_paths: Dict[str, Path], opts: Options) -> None:
    """
    Attach a cover image to MP3 and FLAC outputs via separate remux passes.

    Audio data is copied without re-encoding.  MP3 uses an ffmpeg remux;
    FLAC prefers metaflac when available and falls back to ffmpeg.
    """
    # MP3: APIC frame via ffmpeg remux
    mp3_path = out_paths.get("mp3")
    if mp3_path is not None and mp3_path.is_file() and not opts.dry_run:
        ff = _ffmpeg_base_args(opts, overwrite=True)
        ff += ["-i", str(mp3_path), "-i", str(opts.tag_image)]
        ff += ["-map", "0:a", "-map", "1", "-c", "copy"]
        ff += ["-id3v2_version", "3", "-write_id3v1", "0"]
        ff += _metadata_args(opts)
        ff += [
            "-metadata:s:v", "title=Album cover",
            "-metadata:s:v", "comment=Cover (front)",
            "-disposition:v", "attached_pic",
        ]
        tmp = mp3_path.with_suffix(".tmp" + mp3_path.suffix)
        ff.append(str(tmp))
        _run_verbose(ff, opts, capture_stderr=not opts.verbose)
        if tmp.exists():
            tmp.replace(mp3_path)

    # FLAC: prefer metaflac; fall back to ffmpeg remux
    flac_path = out_paths.get("flac")
    if flac_path is not None and flac_path.is_file() and not opts.dry_run:
        metaflac_bin = _which("metaflac")
        if metaflac_bin is not None:
            _run_verbose(
                [metaflac_bin, "--remove", "--block-type=PICTURE", str(flac_path)],
                opts,
            )
            _run_verbose(
                [metaflac_bin, f"--import-picture-from={opts.tag_image}", str(flac_path)],
                opts,
            )
        else:
            ff = _ffmpeg_base_args(opts, overwrite=True)
            ff += ["-i", str(flac_path), "-i", str(opts.tag_image)]
            ff += ["-map", "0:a", "-map", "1", "-c", "copy"]
            ff += _metadata_args(opts)
            tmp = flac_path.with_suffix(".tmp" + flac_path.suffix)
            ff.append(str(tmp))
            _run_verbose(ff, opts, capture_stderr=not opts.verbose)
            if tmp.exists():
                tmp.replace(flac_path)


def _process_one_midi(midi: Path, opts: Options, sf2: Path) -> None:
    """
    Render a single MIDI file to all requested formats in one pipeline.

    All output formats are encoded by a single fluidsynth -> ffmpeg run.
    When loudnorm is enabled, an optional two-pass loudness analysis is run
    first, then encoding uses per-format filter chains (loudnorm -> alimiter)
    fanned out from a single asplit in filter_complex.
    Overwrite confirmations are collected upfront; if the user declines a
    file it is simply removed from the run rather than aborting everything.
    """

    midi = midi.resolve()
    if not midi.is_file():
        raise Midi2AudioError(f"Input not found: {midi}")

    if opts.out_base is not None:
        base = _strip_audio_ext(opts.out_base)
    else:
        base = midi.with_suffix("")

    # Default: MP3 only if no explicit formats requested
    if not (opts.want_mp3 or opts.want_flac or opts.want_wav or opts.want_raw):
        opts.want_mp3 = True

    # Determine loudnorm filter (when enabled)
    ln_filter: str | None = None
    if opts.enable_loudnorm:
        analysis: Dict[str, float] | None = None
        if opts.two_pass:
            analysis = _analyze_loudness(midi, opts, sf2)
        ln_filter = _build_loudnorm_filter(opts, analysis)

    # Resolve output paths and confirm overwrites for all formats upfront so
    # that fluidsynth is not started only to be blocked mid-stream by a prompt.
    out_paths: Dict[str, Path] = {}
    confirmed_kinds: List[str] = []
    for kind in _collect_kinds(opts):
        out_path = _output_path_for_kind(base, kind)
        if out_path is None:
            continue
        if _confirm_overwrite(out_path, opts):
            out_paths[kind] = out_path
            confirmed_kinds.append(kind)

    if not confirmed_kinds:
        return

    # Single combined fluidsynth -> ffmpeg run
    fs_cmd = _fluidsynth_cmd(midi, opts, sf2)
    ff_cmd = _build_multi_output_ffmpeg(confirmed_kinds, out_paths, ln_filter, opts)
    _run_pipeline(fs_cmd, ff_cmd, opts)

    if opts.tag_image is not None:
        _attach_cover_art(out_paths, opts)


# Argument parsing
# ================


class ArgFormatter(argparse.ArgumentDefaultsHelpFormatter, argparse.RawDescriptionHelpFormatter):
    pass


def _build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="ulsbs-midi2audio",
        description=(
            "Render one or more MIDI files to stereo audio (MP3/FLAC/WAV) "
            "using FluidSynth and FFmpeg."
        ),
        formatter_class=ArgFormatter,
    )

    # Output selection
    p_out = p.add_argument_group("Output selection")
    p_out.add_argument("-m", "--mp3", dest="want_mp3", action="store_true", help="write MP3")
    p_out.add_argument("-f", "--flac", dest="want_flac", action="store_true", help="write FLAC")
    p_out.add_argument("-w", "--wav", dest="want_wav", action="store_true", help="write WAV")
    p_out.add_argument("-k", "--raw", dest="want_raw", action="store_true", help="write pre-filter RAWRENDER.wav")

    # Output quality
    p_qual = p.add_argument_group("Output quality")
    p_qual.add_argument("-B", "--flac-bits", dest="flac_bits", type=int, choices=[16, 24], default=24, help="FLAC bit depth")
    p_qual.add_argument("-U", "--wav-bits", dest="wav_bits", type=int, choices=[16, 24], default=24, help="WAV bit depth")
    p_qual = p.add_argument_group("MP3")
    p_qual.add_argument("-q", "--mp3-vbr-quality", dest="vbr_q", type=int, default=2, metavar="QUALITY", help="MP3 VBR quality 0..9 (lower is better)")
    p_qual.add_argument("-b", "--mp3-cbr-kbps", dest="cbr_kbps", type=int, default=None, metavar="KBPS", help="MP3 CBR kbps 32..320, takes precedence over -q")

    # Rendering
    p_rend = p.add_argument_group("Rendering")
    p_rend.add_argument("-s", "--soundfont-file", dest="sf2", metavar="FILE", help="SoundFont file")
    p_rend.add_argument("-r", "--sample-rate", dest="rate", type=int, default=48_000, help="sample rate (44100/48000/96000/192000)")
    p_rend.add_argument("-g", "--gain", dest="gain", type=float, default=0.60, help="master gain 0.01..1.00")

    # Reverb
    p_rev = p.add_argument_group("Reverb")
    p_rev.add_argument("-R", "--enable-reverb", dest="rev_active", type=int, choices=[0, 1], default=1, help="enable reverb 0/1")
    p_rev.add_argument("--reverb-roomsize", dest="rev_room", type=float, default=0.60, metavar="ROOM-SIZE", help="reverb room size (0.0..1.0)")
    p_rev.add_argument("--reverb-damp", dest="rev_damp", type=float, default=0.30, metavar="DAMPENING", help="reverb dampening (0.0..1.0)")
    p_rev.add_argument("--reverb-level", dest="rev_level", type=float, default=0.60, metavar="LEVEL", help="reverb level (0.0..1.0)")
    p_rev.add_argument("--reverb-width", dest="rev_width", type=float, default=0.90, metavar="WIDTH", help="reverb width (0.0..1.0)")

    # Chorus
    p_chor = p.add_argument_group("Chorus")
    p_chor.add_argument("-c", "--enable-chorus", dest="chorus_active", type=int, choices=[0, 1], default=0, help="enable chorus 0/1")
    p_chor.add_argument("--chorus-lines", dest="chorus_lines", type=int, default=3, metavar="LINES", help="chorus lines (1..99)")
    p_chor.add_argument("--chorus-level", dest="chorus_level", type=float, default=0.60, metavar="LEVEL", help="chorus level (0.0..10.0)")
    p_chor.add_argument("--chorus-speed", dest="chorus_speed", type=float, default=0.20, metavar="SPEED", help="chorus speed (0.1..5.0)")
    p_chor.add_argument("--chorus-depth", dest="chorus_depth", type=float, default=4.25, metavar="DEPTH", help="chorus depth (0.0..256.0)")

    # Loudness
    p_loud = p.add_argument_group("Loudness")
    p_loud.add_argument("-L", "--enable-loudnorm", dest="enable_loudnorm", type=int, choices=[0, 1], default=1, help="enable loudnorm 0/1")
    p_loud.add_argument("-I", "--loudnorm-lufs", dest="lufs", type=float, default=-14.0, help="target LUFS -40..-5")
    p_loud.add_argument("-K", "--loudnorm-lra", dest="lra", type=float, default=7.0, help="target LRA 1..20")
    p_loud.add_argument("-T", "--loudnorm-tp", dest="tp", type=float, default=-0.10, help="true-peak limit -6.0..0.0")
    p_loud.add_argument("-2", "--loudnorm-twopass", dest="two_pass", action="store_true", help="two-pass loudnorm")

    # Limiter
    p_lim = p.add_argument_group("Limiter")
    p_lim.add_argument("-C", "--enable-limiter", dest="clip_guard", type=int, choices=[0, 1], default=0, help="enable post-limiter 0/1")
    p_lim.add_argument("-P", "--limiter-ceiling", dest="guard_tp", type=float, default=0.9, metavar="CEILING", help="limiter ceiling 0.1..1.0")
    p_lim.add_argument("-M", "--limiter-attack", dest="lim_attack", type=float, default=5.0, metavar="ATTACK", help="limiter attack ms")
    p_lim.add_argument("-N", "--limiter-release", dest="lim_release", type=float, default=50.0, metavar="RELEASE", help="limiter release ms")

    # Tags
    p_tags = p.add_argument_group("Tags")
    p_tags.add_argument("--tag-tracktitle", dest="tag_title", metavar="TITLE", help="track title")
    p_tags.add_argument("--tag-trackartist", dest="tag_artist", metavar="ARTIST", help="track artist")
    p_tags.add_argument("--tag-tracknr", dest="tag_tracknr", metavar="NUMBER", help="track number")
    p_tags.add_argument("--tag-albumtitle", dest="tag_album", metavar="ALBUMTITLE", help="album title")
    p_tags.add_argument("--tag-albumartist", dest="tag_albumartist", metavar="ALBUMARTIST", help="album artist")
    p_tags.add_argument("--tag-year", dest="tag_year", metavar="YEAR", help="year")
    p_tags.add_argument("--tag-image", dest="tag_image", metavar="FILE", help="cover image (JPEG/PNG)")

    # Behaviour
    p_beh = p.add_argument_group("Behaviour")
    p_beh.add_argument("-t", "--threads", dest="threads", type=int, default=0, help="ffmpeg threads, 0=auto")
    p_beh.add_argument("-v", "--verbose", dest="verbose", action="store_true", default=False, help="verbose output")
    p_beh.add_argument("-Q", "--quiet", dest="quiet", action="store_true", default=False, help="quiet non-error output")
    p_beh.add_argument("-n", "--dry-run", dest="dry_run", action="store_true", default=False, help="dry-run (print commands only)")
    p_beh.add_argument("-o", "--outfile-basename", dest="out_base", metavar="BASENAME", help="output basename (single input only)")
    p_beh.add_argument("-y", "--force-overwrite", dest="force", action="store_true", help="overwrite existing files without prompting")

    # Positionals
    p.add_argument("inputs", metavar="input.mid", nargs="+", help="MIDI file(s) to render")
    return p


def _opts_from_args(ns: argparse.Namespace) -> Options:
    o = Options()
    o.want_mp3 = bool(ns.want_mp3)
    o.want_flac = bool(ns.want_flac)
    o.want_wav = bool(ns.want_wav)
    o.want_raw = bool(ns.want_raw)
    if ns.out_base:
        o.out_base = Path(ns.out_base)
    o.force = bool(ns.force)

    # Rendering
    o.sf2 = Path(ns.sf2) if ns.sf2 else None
    o.rate = int(ns.rate)
    o.gain = float(ns.gain)

    # Reverb / chorus
    o.rev_active = bool(ns.rev_active)
    o.rev_room = float(ns.rev_room)
    o.rev_damp = float(ns.rev_damp)
    o.rev_level = float(ns.rev_level)
    o.rev_width = float(ns.rev_width)

    o.chorus_active = bool(ns.chorus_active)
    o.chorus_lines = int(ns.chorus_lines)
    o.chorus_level = float(ns.chorus_level)
    o.chorus_speed = float(ns.chorus_speed)
    o.chorus_depth = float(ns.chorus_depth)

    # Loudness
    o.enable_loudnorm = bool(ns.enable_loudnorm)
    o.lufs = float(ns.lufs)
    o.lra = float(ns.lra)
    o.tp = float(ns.tp)
    o.two_pass = bool(ns.two_pass)

    # Limiter
    o.clip_guard = bool(ns.clip_guard)
    o.guard_tp = float(ns.guard_tp)
    o.lim_attack = float(ns.lim_attack)
    o.lim_release = float(ns.lim_release)

    # Bit depths & MP3
    o.flac_bits = int(ns.flac_bits)
    o.wav_bits = int(ns.wav_bits)
    o.vbr_q = int(ns.vbr_q)
    o.cbr_kbps = int(ns.cbr_kbps) if ns.cbr_kbps is not None else None

    # Behaviour
    o.threads = int(ns.threads)
    o.verbose = bool(ns.verbose)
    o.quiet = bool(ns.quiet)
    o.dry_run = bool(ns.dry_run)

    # Tags
    o.tag_title = ns.tag_title
    o.tag_artist = ns.tag_artist
    o.tag_tracknr = ns.tag_tracknr
    o.tag_album = ns.tag_album
    o.tag_albumartist = ns.tag_albumartist
    o.tag_year = ns.tag_year
    if ns.tag_image:
        o.tag_image = Path(ns.tag_image)

    return o


def _validate_options(o: Options, inputs: Sequence[str]) -> None:
    # Sample rate
    if o.rate not in (44_100, 48_000, 96_000, 192_000):
        raise Midi2AudioError(
            f"-r must be one of 44100, 48000, 96000, 192000 (got {o.rate})"
        )

    _float_in_range(o.gain, 0.01, 1.0, "gain (-g)")

    # Reverb / chorus ranges
    for val, lo, hi, name in [
        (o.rev_room, 0.0, 1.0, "reverb roomsize"),
        (o.rev_damp, 0.0, 1.0, "reverb damp"),
        (o.rev_level, 0.0, 1.0, "reverb level"),
        (o.rev_width, 0.0, 1.0, "reverb width"),
        (o.chorus_level, 0.0, 10.0, "chorus level"),
        (o.chorus_speed, 0.1, 5.0, "chorus speed"),
        (o.chorus_depth, 0.0, 256.0, "chorus depth"),
    ]:
        _float_in_range(val, lo, hi, name)

    if not (1 <= o.chorus_lines <= 99):
        raise Midi2AudioError("--chorus-lines must be between 1 and 99")

    # Loudnorm & limiter
    _float_in_range(o.lufs, -40.0, -5.0, "LUFS (-I)")
    _float_in_range(o.lra, 1.0, 20.0, "LRA (-K)")
    _float_in_range(o.tp, -6.0, 0.0, "true peak (-T)")

    _float_in_range(o.guard_tp, 0.1, 1.0, "limiter ceiling (-P)")
    _float_in_range(o.lim_attack, 0.1, 80.0, "limiter attack (-M)")
    _float_in_range(o.lim_release, 1.0, 8000.0, "limiter release (-N)")

    if not (0 <= o.vbr_q <= 9):
        raise Midi2AudioError("-q must be between 0 and 9")
    if o.cbr_kbps is not None and not (32 <= o.cbr_kbps <= 320):
        raise Midi2AudioError("-b must be between 32 and 320 kbps")

    if len(inputs) > 1 and o.out_base is not None:
        raise Midi2AudioError("-o is only allowed with a single input file")


# Main
# ====


def main(argv: Sequence[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]

    if not argv:
        _build_arg_parser().print_help(sys.stderr)
        return 1

    parser = _build_arg_parser()
    ns = parser.parse_args(list(argv))

    opts = _opts_from_args(ns)
    inputs: List[str] = ns.inputs

    try:
        _check_deps()
        _validate_options(opts, inputs)
        sf2 = _find_soundfont(opts.sf2)
    except Midi2AudioError as e:
        sys.stderr.write(f"Error: {e}\n")
        return 2

    if not (opts.want_mp3 or opts.want_flac or opts.want_wav or opts.want_raw):
        opts.want_mp3 = True

    # Auto threads: cores - 1, clamped to [0, 12]
    if opts.threads < 0:
        opts.threads = 0
    if opts.threads == 0:
        try:
            cores = os.cpu_count() or 1
        except Exception:
            cores = 1
        threads = max(0, min(12, cores - 1))
        opts.threads = threads

    for inp in inputs:
        try:
            _process_one_midi(Path(inp), opts, sf2)
        except Midi2AudioError as e:
            sys.stderr.write(f"Error processing {inp}: {e}\n")
            return 12
        except subprocess.CalledProcessError as e:
            sys.stderr.write(
                f"Error processing {inp}: external command failed with code {e.returncode}\n"
            )
            return e.returncode or 12

    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
