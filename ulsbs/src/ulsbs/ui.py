# SPDX-FileCopyrightText: 2016-2026 Lari Natri <lari.natri@iki.fi>
# SPDX-License-Identifier: GPL-3.0-or-later

"""
Terminal UI helpers for consistent, colored output lines.
This file is part of the 'ulsbs' package.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

MAX_COLS = 120
MIN_COLS = 60
PREFIX_LABEL_WIDTH = 9
WRAP_BACKOFF = 15

ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;]*m")


@dataclass
class UI:
    """Small helper for colored, prefixed console messages."""

    use_colors: bool = True

    def __post_init__(self) -> None:
        """
        Init ANSI color codes and prefixes if terminal supports colors.
        Honors the de-facto standard NO_COLOR env var to disable colors.
        """
        self.use_colors = bool(
            self.use_colors and not os.environ.get("NO_COLOR") and self._terminal_supports_colors()
        )
        self._init_colors()

        self.doc_colors = [
            self.C_BROWN,
            self.C_MAGENTA,
            self.C_CYAN,
            self.C_BLUE,
            self.C_YELLOW,
            self.C_LMAGENTA,
            self.C_LCYAN,
            self.C_LBLUE,
        ]

        # Prefix texts without embedded padding; visual width is controlled
        # by PREFIX_LABEL_WIDTH so that all prefixes align.
        self.PRETXT_INFO = self._make_prefix("INFO", self.C_GRAY)
        self.PRETXT_CONTAINER = self._make_prefix("CONT", self.C_WHITE)
        self.PRETXT_GIT = self._make_prefix("GIT", self.C_WHITE)
        self.PRETXT_START = self._make_prefix("START", self.C_GREEN)
        self.PRETXT_EXEC = self._make_prefix("EXEC", self.C_WHITE)
        self.PRETXT_NOEXEC = self._make_prefix("NOEXEC", self.C_DGRAY)
        self.PRETXT_DEPLOY = self._make_prefix("DEPLOY", self.C_WHITE)
        self.PRETXT_NODEPLOY = self._make_prefix("NODEPLOY", self.C_DGRAY)
        self.PRETXT_DEBUG = self._make_prefix("DEBUG", self.C_DGRAY)
        self.PRETXT_WARNING = self._make_prefix("WARNING", self.C_YELLOW)
        self.PRETXT_ERROR = self._make_prefix("ERROR", self.C_RED)
        self.PRETXT_FAIL = self._make_prefix("FAIL", self.C_LRED)
        self.PRETXT_ABORT = self._make_prefix("ABORTED", self.C_LRED)
        self.PRETXT_SUCCESS = self._make_prefix("SUCCESS", self.C_LGREEN)
        self.PRETXT_SEE = self._make_prefix("SEE", self.C_DGRAY)
        self.PRETXT_SPACE = self._make_prefix("", self.C_DGRAY)

    def _terminal_supports_colors(self) -> bool:
        """Detect whether stdout supports ANSI colors."""
        if not sys.stdout.isatty():
            return False
        if os.environ.get("COLORTERM", ""):
            return True
        term = os.environ.get("TERM", "")
        if "xterm" in term and "color" in term:
            return True
        if Path("/usr/bin/tput").exists():
            try:
                subprocess.run(
                    ["tput", "setaf", "1"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=True,
                    timeout=4,
                )
                return True
            except Exception:
                return False
        return False

    def _init_colors(self) -> None:
        """Initialize ANSI color constants based on use_colors flag."""
        if self.use_colors:
            self.C_BLACK = "\033[0;30m"
            self.C_BLUE = "\033[0;34m"
            self.C_GREEN = "\033[0;32m"
            self.C_CYAN = "\033[0;36m"
            self.C_RED = "\033[0;31m"
            self.C_MAGENTA = "\033[0;35m"
            self.C_BROWN = "\033[0;33m"
            self.C_GRAY = "\033[0;37m"
            self.C_DGRAY = "\033[1;30m"
            self.C_LBLUE = "\033[1;34m"
            self.C_LGREEN = "\033[1;32m"
            self.C_LCYAN = "\033[1;36m"
            self.C_LRED = "\033[1;31m"
            self.C_LMAGENTA = "\033[1;35m"
            self.C_YELLOW = "\033[1;33m"
            self.C_WHITE = "\033[1;37m"
            self.C_RESET = "\033[0m"
        else:
            self.C_BLACK = self.C_BLUE = self.C_GREEN = self.C_CYAN = ""
            self.C_RED = self.C_MAGENTA = self.C_BROWN = self.C_GRAY = ""
            self.C_DGRAY = self.C_LBLUE = self.C_LGREEN = self.C_LCYAN = ""
            self.C_LRED = self.C_LMAGENTA = self.C_YELLOW = self.C_WHITE = ""
            self.C_RESET = ""

    def _effective_width(self) -> int:
        """Return the effective column width for wrapping.

        Uses the current terminal width when available, but clamps it
        between MIN_COLS and MAX_COLS. Environment variable
        ULSBS_CLIUI_COLS can be used to override auto-detection, and is
        also clamped to this range. If width cannot be determined,
        falls back to MAX_COLS.
        """

        def clamp(cols: int) -> int:
            return max(MIN_COLS, min(cols, MAX_COLS))

        # Highest priority: explicit override via env var
        env_cols = os.environ.get("ULSBS_CLIUI_COLS")
        if env_cols:
            try:
                cols = int(env_cols)
                if cols > 0:
                    return clamp(cols)
            except ValueError:
                pass

        # Fallback: OS-reported terminal size
        try:
            cols = shutil.get_terminal_size(fallback=(0, 0)).columns
        except OSError:
            cols = 0
        if cols <= 0:
            return MAX_COLS
        return clamp(cols)

    def _build_visible_map(self, s: str) -> tuple[dict[int, int], int]:
        """Return (visible_col -> raw_index_after_char, visible_length)."""
        vis_to_raw: dict[int, int] = {}
        vis_col = 0
        i = 0
        length = len(s)
        while i < length:
            ch = s[i]
            if ch == "\x1b" and i + 1 < length and s[i + 1] == "[":
                # Skip escape sequence like '\x1b[31m'
                j = i + 2
                while j < length and s[j] != "m":
                    j += 1
                i = j + 1  # skip 'm' as well
                continue
            vis_col += 1
            i += 1
            vis_to_raw[vis_col] = i
        return vis_to_raw, vis_col

    def _wrap_segment(self, text: str, content_width: int) -> list[str]:
        """Wrap a single logical line of text, aware of escape sequences."""
        if not text:
            return [""]

        parts: list[str] = []
        rest = text
        while rest:
            vis_map, vis_len = self._build_visible_map(rest)
            if vis_len <= content_width:
                parts.append(rest)
                break

            hard_vis = content_width
            backoff_vis_start = max(1, hard_vis - WRAP_BACKOFF)

            raw_lo = 0
            if backoff_vis_start > 1:
                raw_lo = vis_map.get(backoff_vis_start - 1, len(rest))
            raw_hi = vis_map.get(hard_vis, len(rest))

            space_idx = rest.rfind(" ", raw_lo, raw_hi)
            if space_idx != -1:
                cut_raw = space_idx
                line = rest[:cut_raw].rstrip()
                next_rest = rest[cut_raw + 1 :].lstrip()
            else:
                cut_raw = vis_map.get(hard_vis, len(rest))
                line = rest[:cut_raw].rstrip()
                next_rest = rest[cut_raw:]

            parts.append(line)
            rest = next_rest

        return parts

    def _wrap_message(self, msg: str) -> list[str]:
        """Wrap a message string to fit within the effective width.

        Explicit newlines in the message start new wrapped paragraphs.
        Continuation lines are indented to align with the prefix width.
        Color/escape sequences inside the message are preserved and
        ignored for width calculations.
        """
        width = self._effective_width()
        # Always honour explicit newlines, even if we don't know width
        lines = msg.splitlines()
        if width <= 0:
            return lines or [""]

        # For prefixed lines, we reserve PREFIX_LABEL_WIDTH columns for
        # the prefix itself. For plain() we still use this to keep things
        # consistent and simple.
        content_width = max(10, width - PREFIX_LABEL_WIDTH)

        all_parts: list[str] = []
        if not lines:
            return [""]

        for line in lines:
            all_parts.extend(self._wrap_segment(line, content_width))

        return all_parts

    def _print_line(self, text: str, stderr: bool = False) -> None:
        """Print a single line, stripping ANSI colors if target isn't a TTY."""
        out = sys.stderr if stderr else sys.stdout
        if not out.isatty():
            text = ANSI_ESCAPE_RE.sub("", text)
        print(text, flush=True, file=out)

    def _print_prefixed(self, prefix: str, msg: str, stderr: bool = False) -> None:
        """Print a possibly wrapped, prefixed message.

        The first line uses the given prefix, subsequent lines are
        indented with PRETXT_SPACE.
        """
        parts = self._wrap_message(msg)
        for idx, part in enumerate(parts):
            used_prefix = prefix if idx == 0 else self.PRETXT_SPACE
            self._print_line(f"{used_prefix}{part}", stderr=stderr)

    def _make_prefix(self, label: str, color: str) -> str:
        """Return a colorized, padded prefix of fixed visual width.

        Only the label text is padded/truncated; color escape sequences
        do not contribute to the visual width.
        """
        padded = label[:PREFIX_LABEL_WIDTH].ljust(PREFIX_LABEL_WIDTH)
        return f"{color}{padded}{self.C_RESET}"

    def fmt_doc(self, docname: str, color: str) -> str:
        """Format a document label in a consistent, colored style, and return it."""
        return f"{self.C_DGRAY}[{color}{docname}{self.C_DGRAY}]{self.C_RESET}"

    def fmt_step(self, step: int) -> str:
        """Return given compile step number as colorized string"""
        return self.colorize(f"{step:02d}.", self.C_DGRAY)

    def colorize(self, text: str, color: str) -> str:
        """Wrap a text in a color code and reset suffix and return it."""
        return f"{color}{text}{self.C_RESET}"

    def plain(self, msg: str = "", stderr: bool = False) -> None:
        """Print a plain info line (no prefix)."""
        for part in self._wrap_message(msg):
            self._print_line(part, stderr=stderr)

    def line(self, prefix: str, msg: str, stderr: bool = False) -> None:
        """Print a custom-prefixed line with wrapping support."""
        self._print_prefixed(prefix, msg, stderr=stderr)

    def info_line(self, msg: str, stderr: bool = False) -> None:
        """Print a INFO-prefixed line."""
        self._print_prefixed(self.PRETXT_INFO, msg, stderr=stderr)

    def container_line(self, msg: str, stderr: bool = False) -> None:
        """Print a CONTAINER-prefixed line."""
        self._print_prefixed(self.PRETXT_CONTAINER, msg, stderr=stderr)

    def git_line(self, msg: str, stderr: bool = False) -> None:
        """Print a GIT-prefixed line."""
        self._print_prefixed(self.PRETXT_GIT, msg, stderr=stderr)

    def start_line(self, msg: str, stderr: bool = False) -> None:
        """Print a START-prefixed line."""
        self._print_prefixed(self.PRETXT_START, msg, stderr=stderr)

    def exec_line(self, msg: str, stderr: bool = False) -> None:
        """Print an EXEC-prefixed line."""
        self._print_prefixed(self.PRETXT_EXEC, msg, stderr=stderr)

    def noexec_line(self, msg: str, stderr: bool = False) -> None:
        """Print a NOEXEC-prefixed line."""
        self._print_prefixed(self.PRETXT_NOEXEC, msg, stderr=stderr)

    def deploy_line(self, msg: str, stderr: bool = False) -> None:
        """Print a DEPLOY-prefixed line."""
        self._print_prefixed(self.PRETXT_DEPLOY, msg, stderr=stderr)

    def nodeploy_line(self, msg: str, stderr: bool = False) -> None:
        """Print a NODEPLOY-prefixed line."""
        self._print_prefixed(self.PRETXT_NODEPLOY, msg, stderr=stderr)

    def debug_line(self, msg: str, stderr: bool = False) -> None:
        """Print a DEBUG-prefixed line."""
        self._print_prefixed(self.PRETXT_DEBUG, msg, stderr=stderr)

    def see_line(self, msg: str, stderr: bool = False) -> None:
        """Print a SEE-prefixed line with a path or hint."""
        self._print_prefixed(self.PRETXT_SEE, msg, stderr=stderr)

    def warning_line(self, msg: str, stderr: bool = False) -> None:
        """Print a WARNING-prefixed line."""
        self._print_prefixed(self.PRETXT_WARNING, msg, stderr=stderr)

    def success_line(self, msg: str, stderr: bool = False) -> None:
        """Print a SUCCESS-prefixed line."""
        self._print_prefixed(self.PRETXT_SUCCESS, msg, stderr=stderr)

    def space_line(self, msg: str, stderr: bool = False) -> None:
        """
        Print a line without a prefix, but indented with same amount as other lines.
        Note that this and other *_line() methods support newlines and automatic
        wrapping, and always indent each line printed, so using this method for
        message continuation is not needed.
        """
        self._print_prefixed(self.PRETXT_SPACE, msg, stderr=stderr)

    # The following will be printed to stderr by default

    def error_line(self, msg: str, stderr: bool = True) -> None:
        """Print an ERROR-prefixed line."""
        self._print_prefixed(self.PRETXT_ERROR, msg, stderr=stderr)

    def fail_line(self, msg: str, stderr: bool = True) -> None:
        """Print a FAIL-prefixed line."""
        self._print_prefixed(self.PRETXT_FAIL, msg, stderr=stderr)

    def abort_line(self, msg: str, stderr: bool = True) -> None:
        """Print an ABORTED-prefixed line."""
        self._print_prefixed(self.PRETXT_ABORT, msg, stderr=stderr)
