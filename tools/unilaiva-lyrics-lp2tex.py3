#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# unilaiva-lyrics-lp2tex.py3
#
# Part of Unilaiva songbook system.
#
# Extract lyrics information from Lilypond input in Unilaiva specific format
# and outputs it as a snippet to include in the songbook's TeX files.
#
# Run without arguments for usage info.
#
# Author: Lari Natri
#
# License: GPLv3
#

import sys
import os
import re
import argparse
from typing import List, Tuple, Optional

NUMBER_WORDS = {
    "One": 1, "Two": 2, "Three": 3, "Four": 4, "Five": 5, "Six": 6,
    "Seven": 7, "Eight": 8, "Nine": 9, "Ten": 10, "Eleven": 11, "Twelve": 12
}

# Replacement rules (order matters)
REPLACEMENTS: List[Tuple[str, str]] = [
    (r" -- \| ", "|"),
    (r" -- _ ", ""),
    (r" -- ", ""),
    (r" \| ", " |"),
    (r" __", ""),
    (r" _", ""),
    (r"__ ", ""),
    (r"\|_", "|"),
    (r"\\skip\s+1\s*", ""),     # tolerant for whitespace
    (r'""\s*', ""),             # remove "" even without trailing space
    (r"~", r"\\jw "),
    (r"\\altcol\s*", ""),
]

# Lines to remove entirely (but used as split markers)
REMOVE_LINE_PATTERNS = [
    r"^\s*\\set\s+stanza\s*=.*$",
]

# Find headers like: theLyricsOne = \lyricmode
LYRICS_HEADER_RE = re.compile(
    r"\b(theLyrics(?:One|Two|Three|Four|Five|Six|Seven|Eight|Nine|Ten|Eleven|Twelve))\s*=\s*\\lyricmode\b",
    re.S
)

REPEAT_OPEN_RE = re.compile(r"\\repeat\s+(volta|segno)\s+\d+\s*\{", re.I)

def warn(msg: str):
    print(f"[lp_lyrics_to_tex] {msg}", file=sys.stderr)

def _skip_line_comment(text: str, i: int) -> int:
    # Skip from % to end-of-line
    while i < len(text) and text[i] != '\n':
        i += 1
    return i

def find_next_open_brace_ignoring_comments(text: str, i: int) -> int:
    """Return index of the next '{' after i, ignoring text after '%' on each line."""
    while i < len(text):
        ch = text[i]
        if ch == '%':
            i = _skip_line_comment(text, i)
        elif ch == '{':
            return i
        i += 1
    return -1

def find_matching_brace_ignoring_comments(text: str, start_after_open: int) -> int:
    """
    Given index just after an opening '{', find the index of its matching '}'.
    Ignore braces that appear after '%' on a line. Return index of the '}'.
    """
    depth = 1
    i = start_after_open
    while i < len(text):
        ch = text[i]
        if ch == '%':
            i = _skip_line_comment(text, i)
            continue
        if ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                return i
        i += 1
    raise ValueError("Unbalanced braces in \\lyricmode block")

def extract_lyrics_blocks(content: str) -> List[Tuple[str, str]]:
    """Return list of (block_name, raw_block_text) in file order."""
    blocks: List[Tuple[str, str]] = []
    for m in LYRICS_HEADER_RE.finditer(content):
        name = m.group(1)
        open_brace = find_next_open_brace_ignoring_comments(content, m.end())
        if open_brace == -1:
            warn(f"Could not find '{{' for {name}")
            continue
        close_brace = find_matching_brace_ignoring_comments(content, open_brace + 1)
        raw = content[open_brace + 1: close_brace]
        blocks.append((name, raw))
    warn(f"Found {len}(blocks) theLyrics blocks." if False else f"Found {len(blocks)} theLyrics blocks.")
    return blocks

def strip_and_split_sections(raw_block: str) -> List[str]:
    """Remove stanza lines but treat them as split markers into sections."""
    lines = raw_block.splitlines()
    sections: List[List[str]] = []
    cur: List[str] = []
    stanza_re = re.compile(r"^\s*\\set\s+stanza\s*=")

    for line in lines:
        if stanza_re.match(line):
            if cur:
                sections.append(cur)
            cur = []
        else:
            cur.append(line)
    if cur:
        sections.append(cur)

    sections = [sec for sec in sections if any(s.strip() for s in sec)]
    warn(f"  Sections in block: {len(sections)}")
    return ["\n".join(sec) for sec in sections] if sections else [""]

def classify_and_inline_repeats(section: str) -> Tuple[str, bool]:
    r"""
    Detect whether the *entire* section is wrapped by an outermost \repeat volta/segno.
    Replace inner repeats with \lrep ... \rrep.
    Returns (text_with_inline_repeats, is_outer_repeat)
    """
    text = section
    opens = []
    i = 0
    while i < len(text):
        mo = REPEAT_OPEN_RE.search(text, i)
        if not mo:
            break
        start = mo.start()
        brace_pos = text.find('{', mo.end() - 1)
        if brace_pos == -1:
            break
        close_pos = find_matching_brace_ignoring_comments(text, brace_pos + 1)
        opens.append((start, brace_pos, close_pos + 1))  # [cmd_start, pos_of_{, idx_after_}]
        i = close_pos + 1

    if not opens:
        return (text, False)

    # Check if one repeat span covers the whole section (allowing small leading/trailing whitespace)
    left_nonspace = len(text) - len(text.lstrip())
    right_len = len(text.rstrip())
    begins_at = None
    ends_at = None
    for (cmd_start, brace_pos, after_close) in opens:
        if cmd_start <= left_nonspace + 2 and after_close >= right_len - 2:
            begins_at = cmd_start
            ends_at = after_close
            break

    is_outer = begins_at is not None
    outer_span = (begins_at, ends_at) if is_outer else None

    # Rewrite: remove outermost command braces, inline inner repeats with \lrep ... \rrep
    result = []
    idx = 0
    for (cmd_start, brace_pos, after_close) in sorted(opens, key=lambda t: t[0]):
        close_brace = after_close - 1
        if outer_span and cmd_start == outer_span[0] and after_close == outer_span[1]:
            result.append(text[idx:cmd_start])
            result.append(text[brace_pos + 1:close_brace])
            idx = after_close
        else:
            result.append(text[idx:cmd_start])
            result.append(r"\lrep ")
            result.append(text[brace_pos + 1:close_brace])
            result.append(r" \rrep")
            idx = after_close
    result.append(text[idx:])
    return ("".join(result), is_outer)

def apply_replacements(text: str) -> str:
    # Remove entire lines per rules
    for pat in REMOVE_LINE_PATTERNS:
        text = re.sub(pat, "", text, flags=re.MULTILINE)
    # Inline replacements in order
    for pat, repl in REPLACEMENTS:
        text = re.sub(pat, repl, text)
    # Collapse multiple spaces but keep newlines
    text = re.sub(r"[ \t]+", " ", text)
    # Trim trailing spaces per line
    text = "\n".join(line.rstrip() for line in text.splitlines())
    return text.strip()

def indent_block(text: str, spaces: int = 2) -> str:
    pad = " " * spaces
    lines = text.splitlines()
    return "\n".join(pad + ln.lstrip() if ln.strip() else "" for ln in lines)

def number_from_name(name: str) -> Optional[int]:
    for word, num in NUMBER_WORDS.items():
        if name.endswith(word):
            return num
    return None

def render_section(clean_text: str, is_chorus: bool) -> str:
    env = "chorus" if is_chorus else "verse"
    body = indent_block(clean_text, 2)
    return f"\\begin{env}\n{body}\n\\end{env}"

def process_block(raw_block: str) -> List[Tuple[str, bool]]:
    """Returns a list of (cleaned_section_text, is_chorus)."""
    sections = strip_and_split_sections(raw_block)
    out = []
    for sec in sections:
        with_inline, is_outer = classify_and_inline_repeats(sec)
        cleaned = apply_replacements(with_inline)
        out.append((cleaned, is_outer))
    return out

def main():
    ap = argparse.ArgumentParser(
        description="Extract Unilaiva style LilyPond lyrics to Unilaiva's LaTeX verse/chorus constructs.",
        usage="%(prog)s INPUT.ly [-o OUTPUT.tex]\n       %(prog)s - [-o OUTPUT.tex]  # read from stdin"
    )
    ap.add_argument("input", nargs="?", help="Input .ly file, or '-' to read from stdin")
    ap.add_argument("-o", "--output", help="Output file (default: stdout)")
    args = ap.parse_args()

    if not args.input:
        ap.print_help(sys.stderr)
        sys.exit(1)

    if args.input == "-":
        content = sys.stdin.read()
    else:
        if not os.path.isfile(args.input):
            sys.stderr.write(f"Error: Input file '{args.input}' does not exist or is not a regular file.\n\n")
            ap.print_help(sys.stderr)
            sys.exit(1)
        try:
            with open(args.input, "r", encoding="utf-8") as f:
                content = f.read()
        except OSError as e:
            sys.stderr.write(f"Error: Could not open '{args.input}': {e}\n\n")
            ap.print_help(sys.stderr)
            sys.exit(1)

    blocks = extract_lyrics_blocks(content)
    if not blocks:
        warn("No theLyrics blocks found — is the input the right file?")
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write("")
        return

    # Sort by the number word (One..Twelve)
    blocks.sort(key=lambda kv: (number_from_name(kv[0]) or 999, kv[0]))

    out_lines: List[str] = []
    for name, raw in blocks:
        verse_no = number_from_name(name)
        out_lines.append(f"% verse {verse_no}" if verse_no is not None else f"% {name}")

        sections = process_block(raw)
        rendered_envs = [render_section(txt, is_chorus) for (txt, is_chorus) in sections]

        # Safety: warn if a body somehow contains nested environments
        for r in rendered_envs:
            inner = r.split("\n", 1)[1] if "\n" in r else ""
            if "\\beginverse" in inner or "\\beginchorus" in inner:
                warn("Nested environments detected; flattened rendering applied.")

        out_lines.append(("\\glueverses\n").join(rendered_envs))

    output = "\n".join(out_lines).rstrip() + "\n"
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output)
    else:
        sys.stdout.write(output)

if __name__ == "__main__":
    main()
