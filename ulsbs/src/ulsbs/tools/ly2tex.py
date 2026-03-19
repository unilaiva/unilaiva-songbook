#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2016-2026 Lari Natri <lari.natri@iki.fi>
# SPDX-License-Identifier: GPL-3.0-or-later

"""Convert LilyPond lyrics (\\lyricmode blocks) into ULSBS TeX.

This tool understands a small subset of LilyPond syntax that occurs in the
ULSBS song sources and turns it into a TeX skeleton ready for manual tweaking.
The goal is to get close enough that only light manual editing is
needed for final songbook inclusion.

Supported features:

- \\header: extract title and composer (even when commented).
- \\key and \\time: used to generate key={...} and
  \\meter{X}{Y}.
- \\lyricmode blocks: converted into \\beginverse / \\endverse
  blocks, with \\repeat mapped to \\beginrep / \\endrep and
  \\alternative endings mapped to \\up{n}(...) markers.

This file is part of the ULSBS package, but does not depend on any of it's
components and can be used by itself.

This module is the implementation behind the ulsbs-ly2tex command.
It can also be run directly as:

    python3 -m ulsbs.tools.ly2tex input.tex
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Sequence, Tuple

# Test for python version before importing any package modules.
REQUIRED = (3, 11)
if sys.version_info < REQUIRED:
    sys.stderr.write(
        "This script requires Python {}.{}+, but you are running {}.{}.{}\n".format(
            REQUIRED[0], REQUIRED[1], *sys.version_info[:3]
        )
    )
    raise SystemExit(1)


# Data structures
# ---------------


@dataclass
class TextNode:
    text: str


@dataclass
class RepeatNode:
    children: List["Node"]


Node = TextNode | RepeatNode


@dataclass
class LyricSection:
    varname: str | None
    ordinal: int | None
    index: int  # appearance order
    nodes: List[Node]


# Utilities
# ---------


_NUMBER_WORDS: dict[str, int] = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
    "thirteen": 13,
    "fourteen": 14,
    "fifteen": 15,
    "sixteen": 16,
    "seventeen": 17,
    "eighteen": 18,
    "nineteen": 19,
    "twenty": 20,
}


def _debug(msg: str, enabled: bool) -> None:
    if enabled:
        sys.stderr.write(f"[ly2tex] {msg}\n")


def _find_matching_brace(text: str, open_index: int) -> int:
    if text[open_index] != "{":  # defensive
        raise ValueError("_find_matching_brace called on non-brace position")
    depth = 1
    i = open_index + 1
    n = len(text)
    while i < n and depth:
        c = text[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
        i += 1
    if depth != 0:
        raise ValueError("Unbalanced braces in lyric block")
    return i - 1


# Header / metadata parsing
# -------------------------


_HEADER_RE = re.compile(r"^\s*%?\s*\\header\s*\{(.*?)^\s*%?\s*}\s*", re.DOTALL | re.MULTILINE)
_TITLE_RE = re.compile(r"^\s*%?\s*title\s*=\s*\"([^\"]*)\"", re.MULTILINE)
_COMPOSER_RE = re.compile(r"^\s*%?\s*composer\s*=\s*\"([^\"]*)\"", re.MULTILINE)


def parse_header(src: str, debug: bool) -> Tuple[str, str | None]:
    """Return (title, composer_or_none). Defaults to ("unknown", None)."""

    title = "unknown"
    composer: str | None = None

    m = _HEADER_RE.search(src)
    if not m:
        _debug("No \\header block found", debug)
        return title, composer

    body = m.group(1)
    mt = _TITLE_RE.search(body)
    if mt:
        title = mt.group(1).strip() or title
    mc = _COMPOSER_RE.search(body)
    if mc:
        composer = mc.group(1).strip() or None

    _debug(f"Header parsed: title={title!r}, composer={composer!r}", debug)
    return title, composer


def parse_key_and_time(src: str, debug: bool) -> Tuple[str | None, Tuple[int, int] | None]:
    """Return (key_option, meter_tuple) where key_option is e.g. 'C' or 'Am'."""

    # First \key <note> \major|\minor we can find
    key_match = re.search(r"\\key\s+([a-gA-G])[^\\\s]*\s+\\(major|minor)", src)
    key_opt: str | None = None
    if key_match:
        note = key_match.group(1).upper()
        mode = key_match.group(2)
        val = note + ("m" if mode == "minor" else "")
        key_opt = val
        _debug(f"Found key: {note} {mode} -> {key_opt}", debug)
    else:
        _debug("No \\key found", debug)

    time_match = re.search(r"\\time\s+(\d+)\s*/\s*(\d+)", src)
    meter: Tuple[int, int] | None = None
    if time_match:
        meter = (int(time_match.group(1)), int(time_match.group(2)))
        _debug(f"Found time: {meter[0]}/{meter[1]}", debug)
    else:
        _debug("No \\time found", debug)

    return key_opt, meter


# Lyrics cleaning
# ---------------


_STANZA_RE = re.compile(r"\\set\s+stanza\s*=\s*(?:\"[^\"]*\"|'[^']*'|#[^ \t\r\n]+|\S+)\s*")
_STANZA_ASSIGN_RE = re.compile(r"\bstanza\s*=\s*(?:\"[^\"]*\"|'[^']*'|#[^ \t\r\n]+|\S+)\s*")


def clean_lyrics_fragment(raw: str) -> str:
    """Apply the LilyPond -> TeX lyric clean-up rules."""

    # Strip comments
    raw = re.sub(r"%.*", "", raw)

    # LilyPond ignores line breaks for lyrics; treat them as spaces
    text = raw.replace("\r", " ").replace("\n", " ")

    # Remove explicit stanza labels completely (e.g. \\set stanza = "1.")
    text = _STANZA_RE.sub(" ", text)
    # Also catch any leftover 'stanza = ...' fragments if \\set was stripped separately
    text = _STANZA_ASSIGN_RE.sub(" ", text)

    # Normalise tabs
    text = text.replace("\t", " ")

    # 1–3: hyphen / barline handling
    text = text.replace(" -- | ", "|")
    text = text.replace(" -- _ ", "")
    text = text.replace(" -- ", "")

    # 4: slightly normalise spaces around barlines
    text = text.replace(" | ", " |")

    # 5–8: underscores / melismas
    text = text.replace(" __", "")
    text = text.replace(" _", "")
    text = text.replace("__ ", "")
    text = text.replace("|_", "|")

    # 9: skips
    text = text.replace("\\skip 1 ", "")

    # 10: empty lyric placeholders
    text = text.replace('"" ', "")
    text = text.replace('""', "")

    # 11: tie within a word / phrase
    text = text.replace("~", "\\jw ")

    # 12: colour helpers used in some sources
    text = text.replace("\\altcol ", "")

    # 13–14: punctuation that should disappear
    text = text.replace(".", "")
    text = text.replace(";", "")

    # Remove other LilyPond commands (but keep TeX macros we emit later)
    text = re.sub(r"\\(?!jw\b|up\b)[A-Za-z][A-Za-z0-9_]*", "", text)

    # Collapse whitespace
    text = re.sub(r"\s+", " ", text).strip()

    return text


# Lyric body parsing (repeat / alternative)
# -----------------------------------------


def _process_alternative_block(block: str, debug: bool) -> str:
    r"""Convert an \alternative { {a} {b} } lyrics block.

    If all cleaned alternatives are identical, returns that text as if
    there were no alternatives. Otherwise returns a string with
    shared-prefix handling and \up{n}(...) markers.
    """

    branches: List[str] = []
    i = 0
    n = len(block)
    while i < n:
        while i < n and block[i].isspace():
            i += 1
        if i >= n:
            break
        if block[i] != "{":
            # Fallback: treat whole block as normal text
            _debug("Unexpected syntax inside \\alternative; falling back to plain text", debug)
            return clean_lyrics_fragment(block)
        close = _find_matching_brace(block, i)
        branches.append(block[i + 1 : close])
        i = close + 1

    if not branches:
        return ""

    cleaned_full = [clean_lyrics_fragment(b) for b in branches]
    cleaned_stripped = [c.strip() for c in cleaned_full if c.strip()]

    if not cleaned_stripped:
        return ""

    first = cleaned_stripped[0]
    if all(c == first for c in cleaned_stripped):
        # All endings textually the same -> behave as if no alternative
        _debug("All alternative endings identical; flattening", debug)
        return first

    # Different endings: convert to \up{n}(...) annotations.
    # Try to find a common prefix (often a leading '|').
    prefix = os.path.commonprefix(cleaned_full)
    payloads = [c[len(prefix) :].strip() for c in cleaned_full]

    up_parts: List[str] = []
    for idx, payload in enumerate(payloads, start=1):
        if not payload:
            continue
        up_parts.append(f"\\up{{{idx}}}({payload})")

    if not up_parts:
        return prefix

    if prefix.endswith("|"):
        # Glue first marker directly after the barline
        result = prefix + up_parts[0]
        if len(up_parts) > 1:
            result += " " + " ".join(up_parts[1:])
        return result

    if prefix:
        return prefix + " " + " ".join(up_parts)
    return " ".join(up_parts)


def _parse_lyrics_block(body: str, debug: bool) -> List[Node]:
    """Parse the inside of a \\lyricmode { ... } block.

    Produces a small AST with TextNode and RepeatNode objects, with all
    plain-text segments already cleaned.
    """

    nodes: List[Node] = []
    current_raw: List[str] = []

    i = 0
    n = len(body)
    while i < n:
        c = body[i]
        if c == "\\":
            # Possible control sequence
            if body.startswith("\\repeat", i):
                # Flush pending text
                if current_raw:
                    txt = clean_lyrics_fragment("".join(current_raw))
                    if txt:
                        nodes.append(TextNode(txt))
                    current_raw = []

                i += len("\\repeat")
                # Skip repeat type and count until the body "{".
                while i < n and body[i].isspace():
                    i += 1
                while i < n and not body[i].isspace() and body[i] != "{":
                    i += 1  # repeat kind (volta, segno, etc.)
                while i < n and body[i].isspace():
                    i += 1
                while i < n and body[i] != "{":
                    i += 1
                if i >= n or body[i] != "{":
                    _debug("Malformed \\repeat (missing body); treating as text", debug)
                    current_raw.append("\\repeat")
                    continue
                open_brace = i
                close_brace = _find_matching_brace(body, open_brace)
                inner = body[open_brace + 1 : close_brace]
                child_nodes = _parse_lyrics_block(inner, debug)
                nodes.append(RepeatNode(child_nodes))
                i = close_brace + 1
                continue

            if body.startswith("\\alternative", i):
                # Flush pending text
                if current_raw:
                    txt = clean_lyrics_fragment("".join(current_raw))
                    if txt:
                        nodes.append(TextNode(txt))
                    current_raw = []

                i += len("\\alternative")
                while i < n and body[i].isspace():
                    i += 1
                if i >= n or body[i] != "{":
                    _debug("Malformed \\alternative (missing block); treating as text", debug)
                    current_raw.append("\\alternative")
                    continue
                open_brace = i
                close_brace = _find_matching_brace(body, open_brace)
                block = body[open_brace + 1 : close_brace]
                alt_text = _process_alternative_block(block, debug)
                if alt_text:
                    nodes.append(TextNode(alt_text))
                i = close_brace + 1
                continue

            # Other commands: just add to raw; cleaner will strip them
            current_raw.append(c)
            i += 1
        else:
            current_raw.append(c)
            i += 1

    if current_raw:
        txt = clean_lyrics_fragment("".join(current_raw))
        if txt:
            nodes.append(TextNode(txt))

    return nodes


# Top-level lyric section discovery
# ---------------------------------


_LYRICMODE_RE = re.compile(
    r"(?:(?P<var>[A-Za-z_][A-Za-z0-9_]*)\s*=\s*)?\\lyricmode\s*{",
    re.MULTILINE,
)


def _extract_lyric_sections(src: str, debug: bool) -> List[LyricSection]:
    sections: List[LyricSection] = []
    pos = 0
    idx = 0
    n = len(src)

    while True:
        m = _LYRICMODE_RE.search(src, pos)
        if not m:
            break
        varname = m.group("var")
        open_brace = src.find("{", m.end() - 1)
        if open_brace == -1:
            break
        close_brace = _find_matching_brace(src, open_brace)
        body = src[open_brace + 1 : close_brace]

        # Ordinal from variable name like theLyricsOne, theLyricsTwo, ...
        ord_val: int | None = None
        if varname:
            m_ord = re.match(r"theLyrics([A-Za-z]+)$", varname)
            if m_ord:
                word = m_ord.group(1).lower()
                ord_val = _NUMBER_WORDS.get(word)

        nodes = _parse_lyrics_block(body, debug)
        sections.append(LyricSection(varname=varname, ordinal=ord_val, index=idx, nodes=nodes))

        _debug(
            f"Found lyric section {idx}: varname={varname!r}, ordinal={ord_val}",
            debug,
        )

        idx += 1
        pos = close_brace + 1
        if pos >= n:
            break

    return sections


# Rendering
# ---------


def _render_nodes(nodes: List[Node], base_indent: int = 0) -> List[str]:
    """Render nodes into TeX lines with indentation.

    base_indent is the indentation level (0 = no indent). Inside a
    repeat block we increase the indentation by one level so that the
    resulting TeX is easier to read.
    """

    lines: List[str] = []
    indent = "  " * base_indent
    for node in nodes:
        if isinstance(node, TextNode):
            if node.text:
                # If the lyric line (ignoring trailing whitespace) ends with
                # a barline character |, append " \\e" signify that the bar
                # continues on the next line.
                text = node.text.rstrip()
                if text.endswith("|"):
                    text += " \\e"
                lines.append(indent + text)
        elif isinstance(node, RepeatNode):
            lines.append(indent + "\\beginrep")
            lines.extend(_render_nodes(node.children, base_indent + 1))
            lines.append(indent + "\\endrep")
    return lines


def convert_ly_to_tex(src: str, debug: bool = False) -> str:
    title, composer = parse_header(src, debug)
    key_opt, meter = parse_key_and_time(src, debug)
    sections = _extract_lyric_sections(src, debug)

    # Order sections: first those with a known ordinal, sorted numerically;
    # then any remaining sections in source order.
    sections_sorted = sorted(
        sections,
        key=lambda s: (s.ordinal is None, s.ordinal if s.ordinal is not None else s.index),
    )

    lines: List[str] = []

    # \beginsong line
    opt_parts: List[str] = []
    if composer:
        # Use braces so the value is typeset verbatim
        opt_parts.append(f"by={{{composer}}}")
    if key_opt:
        opt_parts.append(f"key={{{key_opt}}}")

    if opt_parts:
        lines.append(f"\\beginsong{{{title}}}[{', '.join(opt_parts)}]")
    else:
        lines.append(f"\\beginsong{{{title}}}")

    # Meter
    if meter is not None:
        num, den = meter
        lines.append(f"  \\meter{{{num}}}{{{den}}}")

    # Verses
    for idx, sec in enumerate(sections_sorted, start=1):
        lines.append(f"  % verse {idx}:")
        lines.append("  \\beginverse")
        verse_lines = _render_nodes(sec.nodes, base_indent=2)
        if verse_lines:
            # If there's only a single repeat, it will already have beginrep/endrep
            for ln in verse_lines:
                lines.append(ln)
        lines.append("  \\endverse")

    lines.append("\\endsong")

    return "\n".join(lines) + "\n"


# CLI
# ---


def _build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="ulsbs-ly2tex",
        description="Convert LilyPond lyrics (\\lyricmode blocks) into ULSBS TeX skeleton.",
    )
    p.add_argument(
        "input",
        metavar="INPUT.ly",
        help="LilyPond file to read, or '-' for stdin",
    )
    p.add_argument(
        "-o",
        "--output-file",
        dest="output_file",
        metavar="OUT.tex",
        type=Path,
        help="Write output to this file instead of stdout",
    )
    p.add_argument(
        "--debug",
        action="store_true",
        help="Print parsing debug information to stderr",
    )
    return p


def main(argv: Sequence[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]

    parser = _build_arg_parser()
    ns = parser.parse_args(list(argv))

    debug = bool(ns.debug)

    try:
        if ns.input == "-":
            src = sys.stdin.read()
        else:
            path = Path(ns.input)
            if not path.exists():
                raise FileNotFoundError(f"Input file not found: {path}")
            src = path.read_text(encoding="utf-8")

        tex = convert_ly_to_tex(src, debug=debug)

        if ns.output_file is not None:
            ns.output_file.write_text(tex, encoding="utf-8")
        else:
            sys.stdout.write(tex)

        return 0

    except Exception as exc:
        sys.stderr.write(f"Error: {exc}\n")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
