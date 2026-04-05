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
import hashlib
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, TextIO

if TYPE_CHECKING:  # pragma: no cover - import only for type checking
    from .jobs import Job

MAX_COLS = 120
MIN_COLS = 60
PREFIX_LABEL_WIDTH = 9
WRAP_BACKOFF = 15

ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;]*m")

# ANSI reset sequence used by UI.colorize; kept here so the spinner can
# detect and preserve trailing reset codes when appending dots.
_ANSI_RESET = "\033[0m"

_SPINNER_MAX_DOTS = 9
_SPINNER_INTERVAL_SEC = 0.1

_output_lock = threading.RLock()

_spinner_active: bool = False
_spinner_supported: bool | None = None
_spinner_text: str | None = None
_spinner_spin: bool = True
_spinner_dots: int = 0
_spinner_last_width: int = 0
_spinner_thread: threading.Thread | None = None
_spinner_stop_event: threading.Event | None = None

# Track whether we've hidden the terminal cursor while the spinner is active.
_cursor_hidden: bool = False

_original_stdout: TextIO = sys.stdout
_original_stderr: TextIO = sys.stderr
_stdout_wrapper: "_SpinnerStream" | None = None
_stderr_wrapper: "_SpinnerStream" | None = None


def _detect_spinner_supported() -> bool:
    global _spinner_supported
    if _spinner_supported is not None:
        return _spinner_supported
    try:
        if not sys.stdout.isatty():
            _spinner_supported = False
        else:
            term = os.environ.get("TERM", "")
            if term == "dumb":
                _spinner_supported = False
            elif os.environ.get("ULSBS_NOSPINNER"):
                _spinner_supported = False
            else:
                _spinner_supported = True
    except Exception:
        _spinner_supported = False
    return _spinner_supported


def _patch_streams_for_spinner() -> None:
    global _original_stdout, _original_stderr, _stdout_wrapper, _stderr_wrapper
    if isinstance(sys.stdout, _SpinnerStream) and isinstance(sys.stderr, _SpinnerStream):
        return
    _original_stdout = sys.stdout  # type: ignore[assignment]
    _original_stderr = sys.stderr  # type: ignore[assignment]
    _stdout_wrapper = _SpinnerStream(_original_stdout, is_stderr=False)
    _stderr_wrapper = _SpinnerStream(_original_stderr, is_stderr=True)
    sys.stdout = _stdout_wrapper  # type: ignore[assignment]
    sys.stderr = _stderr_wrapper  # type: ignore[assignment]


def _spinner_frame_text_unlocked() -> str:
    """Build the visible spinner text (base text + optional dots).

    If the base text ends with the standard ANSI reset sequence, dots are
    inserted *before* that reset so they inherit the same color. This
    allows callers (e.g. UI.start_spinner) to simply pass in a string
    produced by UI.colorize() and still have colored dots.
    """
    base = _spinner_text or ""
    dots = "." * _spinner_dots if _spinner_spin else ""
    if not dots:
        return base
    if base.endswith(_ANSI_RESET):
        core = base[: -len(_ANSI_RESET)]
        return f"{core}{dots}{_ANSI_RESET}"
    return f"{base}{dots}"


def _hide_cursor_unlocked() -> None:
    """Hide the terminal cursor if it is currently visible.

    Uses the standard ANSI sequence CSI ?25l. Any errors are swallowed.
    """
    global _cursor_hidden
    if _cursor_hidden:
        return
    try:
        _original_stdout.write("\033[?25l")
        _original_stdout.flush()
        _cursor_hidden = True
    except Exception:
        # Never let spinner failures crash the program
        _cursor_hidden = False


def _show_cursor_unlocked() -> None:
    """Show the terminal cursor again if we previously hid it."""
    global _cursor_hidden
    if not _cursor_hidden:
        return
    try:
        _original_stdout.write("\033[?25h")
        _original_stdout.flush()
    except Exception:
        # Ignore errors; leave flag reset so we don't spam sequences
        pass
    finally:
        _cursor_hidden = False


def _clear_current_line_unlocked() -> None:
    """Clear the current terminal line used by the spinner.

    Uses a carriage return and ANSI clear-to-eol so that we do not
    leave leading spaces that might visually prefix subsequent output
    lines. Any errors are swallowed.
    """
    try:
        _original_stdout.write("\r\033[K")
        _original_stdout.flush()
    except Exception:
        # Never let spinner failures crash the program
        pass


def _draw_spinner_frame_unlocked(initial: bool) -> None:
    global _spinner_last_width, _spinner_active
    try:
        text = _spinner_frame_text_unlocked()
        if not text:
            return
        # Always return to column 0 and clear to end-of-line before drawing,
        # which guarantees that shorter updates do not leave trailing junk.
        _original_stdout.write("\r\033[K" + text)
        _original_stdout.flush()
        _spinner_last_width = len(text)
    except Exception:
        _spinner_active = False
        _show_cursor_unlocked()


class _SpinnerStream:
    """Wrapper for stdout/stderr that cooperates with the spinner.

    It ensures that any normal line-oriented output appears above the
    spinner line, and that the spinner is re-drawn afterwards.
    """

    def __init__(self, wrapped: TextIO, is_stderr: bool) -> None:
        self._wrapped = wrapped
        self._is_stderr = is_stderr
        # Track whether the next non-empty write begins a new terminal line.
        self._at_line_start = True
        # Thread id of the writer that last produced non-empty content.
        # Used to keep whole-line writes from different threads from
        # being glued together when their print() calls overlap.
        self._last_writer_tid: int | None = None
        # Threads for which we have already auto-inserted a newline to
        # terminate their previous line. For these, we suppress the next
        # leading "\n" write so that we do not end up with a blank line.
        self._auto_wrapped_tids: set[int] = set()

    def _update_line_state(self, s: str) -> None:
        """Update internal flag tracking if we are at the start of a line."""
        last_nl = s.rfind("\n")
        last_cr = s.rfind("\r")
        last_pos = max(last_nl, last_cr)
        if last_pos == -1:
            # No newline/carriage return seen -> we are mid-line
            self._at_line_start = False
        else:
            # We are at line start only if the *last* char written is a newline/CR
            self._at_line_start = last_pos == len(s) - 1

    def write(self, s: str) -> int:
        if not s:
            return 0
        if not _spinner_active:
            n = self._wrapped.write(s)
            self._update_line_state(s)
            return n
        with _output_lock:
            if not _spinner_active:
                n = self._wrapped.write(s)
                self._update_line_state(s)
                return n

            # If a different thread starts writing while we are in the middle
            # of a line, terminate the previous logical line first so that
            # outputs from concurrent jobs never appear glued together.
            tid = threading.get_ident()
            # If we previously auto-wrapped a line for this thread, and its
            # next write is only a newline, drop that newline to avoid a
            # visually empty line. This matches how print() splits writes
            # into "text" and "\n".
            if tid in self._auto_wrapped_tids and s in ("\n", "\r", "\r\n"):
                self._auto_wrapped_tids.discard(tid)
                # State already reflects that we are at a new line start
                # because we injected the newline earlier.
                return len(s)

            if (
                self._last_writer_tid is not None
                and self._last_writer_tid != tid
                and not self._at_line_start
                and any(ch not in ("\n", "\r") for ch in s)
            ):
                prev_tid = self._last_writer_tid
                try:
                    self._wrapped.write("\n")
                    self._wrapped.flush()
                except Exception:
                    pass
                # Remember that we closed prev_tid's line for it, so that we
                # can drop its own trailing "\n" and avoid a blank line.
                if prev_tid is not None:
                    self._auto_wrapped_tids.add(prev_tid)
                # We are now logically at the start of a new line.
                self._at_line_start = True

            self._last_writer_tid = tid

            # Only clear the spinner line when we are truly at the start of a
            # new line *and* this write actually contains some non-newline
            # content. This avoids wiping freshly printed text when higher
            # layers issue separate writes for text and for the trailing "\n".
            if self._at_line_start and any(ch not in ("\n", "\r") for ch in s):
                _clear_current_line_unlocked()

            n = self._wrapped.write(s)
            try:
                self._wrapped.flush()
            except Exception:
                pass

            # If we just finished a line and spinner is still active,
            # re-draw it on the next line.
            if _spinner_active and s.endswith("\n"):
                _draw_spinner_frame_unlocked(initial=True)

            self._update_line_state(s)
            return n

    def flush(self) -> None:
        try:
            self._wrapped.flush()
        except Exception:
            pass

    def isatty(self) -> bool:  # pragma: no cover - thin wrapper
        try:
            return self._wrapped.isatty()
        except Exception:
            return False

    def fileno(self) -> int:  # pragma: no cover - thin wrapper
        return self._wrapped.fileno()

    def __getattr__(self, name: str) -> object:
        return getattr(self._wrapped, name)


def _spinner_thread_main() -> None:
    """
    Background worker function for the spinner thread.

    This loop periodically updates the spinner state and redraws the spinner
    frame while _spinner_active and _spinner_spin are True. It terminates
    when _spinner_stop_event is set, or when the spinner is deactivated.
    """
    global _spinner_dots, _spinner_active, _spinner_stop_event
    try:
        while True:
            if _spinner_stop_event is not None and _spinner_stop_event.is_set():
                break
            time.sleep(_SPINNER_INTERVAL_SEC)
            with _output_lock:
                if not _spinner_active:
                    break
                if not _spinner_spin:
                    continue
                _spinner_dots = (_spinner_dots + 1) % (_SPINNER_MAX_DOTS + 1)
                _draw_spinner_frame_unlocked(initial=False)
    except Exception:
        # Spinner failures must never crash the program
        with _output_lock:
            _spinner_active = False
            _show_cursor_unlocked()
    finally:
        # On any exit path, make sure the cursor is visible again.
        with _output_lock:
            _show_cursor_unlocked()


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

        # Palette of colors used to assign each document a stable color.
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

        # Mapping from document stem -> color, kept stable for the duration
        # of the process so each songbook keeps its own color.
        self._doc_stem_colors: dict[str, str] = {}

        # Fixed colors for known variants; unknown/empty variants fall back
        # to gray. These are used for the ":<variant>" suffix in fmt_doc().
        self._variant_colors: dict[str, str] = {
            "default": self.C_GREEN,
            "lyrics": self.C_YELLOW,
            "charango": self.C_MAGENTA,
            "bassclef": self.C_BROWN,
        }

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

    def _color_for_doc_stem(self, stem: str) -> str:
        """Return a stable color for the given document stem.

        The mapping is cached in _doc_stem_colors and based on a
        deterministic hash so that it does not depend on job ordering.
        """
        if stem in self._doc_stem_colors:
            return self._doc_stem_colors[stem]

        if not self.doc_colors:
            color = self.C_WHITE
        else:
            idx = int(hashlib.blake2b(stem.encode("utf-8")).hexdigest(), 16) % len(self.doc_colors)
            color = self.doc_colors[idx]

        self._doc_stem_colors[stem] = color
        return color

    def _color_for_variant(self, variant: str | None) -> str:
        """Return the color used for the variant label in fmt_doc()."""
        if not variant:
            return self.C_GRAY
        return self._variant_colors.get(variant, self.C_GRAY)

    # BEGIN spinner

    def start_spinner(self, txt: str | None = None, spin: bool = True) -> None:
        """Start or update a status spinner on the last output line.

        When enabled and supported by the current TTY, this shows an
        animated dotted spinner (0..5 dots) after the given text. The
        spinner line is kept at the bottom of the output while other
        threads print lines using either this UI or plain print().

        If output is not a TTY or the spinner cannot be used, this is a
        no-op. Any internal errors while starting the spinner are
        swallowed so that they never crash the program.
        """
        global _spinner_active, _spinner_text, _spinner_spin, _spinner_dots
        global _spinner_thread, _spinner_stop_event, _spinner_last_width

        if not _detect_spinner_supported():
            return

        with _output_lock:
            _patch_streams_for_spinner()
            _spinner_text = txt or ""
            _spinner_spin = bool(spin)
            _spinner_dots = 0
            _spinner_last_width = 0

            if _spinner_active:
                # Just update text/flags; frame will be redrawn by thread
                if spin and _spinner_thread is None and _spinner_stop_event is not None:
                    _spinner_thread = threading.Thread(
                        target=_spinner_thread_main,
                        name="ulsbs-spinner",
                        daemon=True,
                    )
                    try:
                        _spinner_thread.start()
                    except Exception:
                        _spinner_thread = None
                _draw_spinner_frame_unlocked(initial=False)
                return

            _spinner_active = True
            _spinner_stop_event = threading.Event()

            try:
                # Make sure any previously buffered output is visible
                _original_stdout.flush()
            except Exception:
                _spinner_active = False
                _spinner_stop_event = None
                return

            # Hide cursor while spinner is visible
            _hide_cursor_unlocked()

            _draw_spinner_frame_unlocked(initial=True)

            if spin:
                _spinner_thread = threading.Thread(
                    target=_spinner_thread_main,
                    name="ulsbs-spinner",
                    daemon=True,
                )
                try:
                    _spinner_thread.start()
                except Exception:
                    # Best-effort: disable spinner but keep the program running
                    _spinner_thread = None
                    _spinner_active = False
                    _spinner_stop_event = None

    def stop_spinner(self) -> None:
        """Stop and clear the status spinner, if it is currently active.

        This is safe to call even if the spinner was never started or
        has already been stopped; in those cases it is a no-op.
        """
        global _spinner_active, _spinner_thread, _spinner_stop_event

        with _output_lock:
            if not _spinner_active:
                return
            _spinner_active = False
            stop_event = _spinner_stop_event
            thread = _spinner_thread
            _spinner_stop_event = None
            _spinner_thread = None

        if stop_event is not None:
            try:
                stop_event.set()
            except Exception:
                pass
        if thread is not None:
            try:
                thread.join(timeout=0.5)
            except Exception:
                pass

        with _output_lock:
            try:
                _clear_current_line_unlocked()
                _show_cursor_unlocked()
                _original_stdout.flush()
            except Exception:
                pass

    # END spinner

    def fmt_doc(self, job: "Job") -> str:
        """Format a document label for a Job in a consistent, colored style.

        The document stem is colored per-book (stable across the run), and
        the :<variant> suffix is colored using a fixed mapping.
        """
        doc_color = self._color_for_doc_stem(job.doc_stem)
        variant = job.variant

        if variant:
            variant_color = self._color_for_variant(variant)
            inner = f"{doc_color}{job.doc_stem}{self.C_DGRAY}:{variant_color}{variant}{self.C_DGRAY}"
        else:
            inner = f"{doc_color}{job.doc_stem}{self.C_DGRAY}"

        return f"{self.C_DGRAY}[{inner}]{self.C_RESET}"

    def fmt_step(self, step: int) -> str:
        """Return given compile step number as colorized string"""
        return self.colorize(f"{step:02d}:", self.C_DGRAY)

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
