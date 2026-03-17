# SPDX-FileCopyrightText: 2016-2026 Lari Natri <lari.natri@iki.fi>
# SPDX-License-Identifier: GPL-3.0-or-later

"""
Terminal UI helpers for consistent, colored output lines.
This file is part of the 'ulsbs' package.
"""

from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


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
            self.use_colors
            and not os.environ.get("NO_COLOR")
            and self._terminal_supports_colors()
        )
        self._init_colors()

        self.doc_colors = [
            self.C_BROWN, self.C_MAGENTA, self.C_CYAN, self.C_BLUE,
            self.C_YELLOW, self.C_LMAGENTA, self.C_LCYAN, self.C_LBLUE
        ]

        self.PRETXT_INFO      = f"{self.C_GRAY}INFO     {self.C_RESET}"
        self.PRETXT_CONTAINER = f"{self.C_WHITE}CONT     {self.C_RESET}"
        self.PRETXT_GIT       = f"{self.C_WHITE}GIT      {self.C_RESET}"
        self.PRETXT_START     = f"{self.C_GREEN}START    {self.C_RESET}"
        self.PRETXT_EXEC      = f"{self.C_WHITE}EXEC     {self.C_RESET}"
        self.PRETXT_NOEXEC    = f"{self.C_DGRAY}NOEXEC   {self.C_RESET}"
        self.PRETXT_DEPLOY    = f"{self.C_WHITE}DEPLOY   {self.C_RESET}"
        self.PRETXT_NODEPLOY  = f"{self.C_DGRAY}NODEPLOY {self.C_RESET}"
        self.PRETXT_DEBUG     = f"{self.C_DGRAY}DEBUG    {self.C_RESET}"
        self.PRETXT_WARNING   = f"{self.C_YELLOW}WARNING  {self.C_RESET}"
        self.PRETXT_ERROR     = f"{self.C_RED}ERROR    {self.C_RESET}"
        self.PRETXT_FAIL      = f"{self.C_LRED}FAIL     {self.C_RESET}"
        self.PRETXT_ABORT     = f"{self.C_LRED}ABORTED  {self.C_RESET}"
        self.PRETXT_SUCCESS   = f"{self.C_LGREEN}SUCCESS  {self.C_RESET}"
        self.PRETXT_SEE       = f"{self.C_DGRAY}SEE      {self.C_RESET}"
        self.PRETXT_SPACE     = f"{self.C_DGRAY}         {self.C_RESET}"


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
                subprocess.run(["tput", "setaf", "1"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True, timeout=4)
                return True
            except Exception:
                return False
        return False

    def _init_colors(self) -> None:
        """Initialize ANSI color constants based on use_colors flag."""
        if self.use_colors:
            self.C_BLACK    = "\033[0;30m"
            self.C_BLUE     = "\033[0;34m"
            self.C_GREEN    = "\033[0;32m"
            self.C_CYAN     = "\033[0;36m"
            self.C_RED      = "\033[0;31m"
            self.C_MAGENTA  = "\033[0;35m"
            self.C_BROWN    = "\033[0;33m"
            self.C_GRAY     = "\033[0;37m"
            self.C_DGRAY    = "\033[1;30m"
            self.C_LBLUE    = "\033[1;34m"
            self.C_LGREEN   = "\033[1;32m"
            self.C_LCYAN    = "\033[1;36m"
            self.C_LRED     = "\033[1;31m"
            self.C_LMAGENTA = "\033[1;35m"
            self.C_YELLOW   = "\033[1;33m"
            self.C_WHITE    = "\033[1;37m"
            self.C_RESET    = "\033[0m"
        else:
            self.C_BLACK = self.C_BLUE = self.C_GREEN = self.C_CYAN = ""
            self.C_RED = self.C_MAGENTA = self.C_BROWN = self.C_GRAY = ""
            self.C_DGRAY = self.C_LBLUE = self.C_LGREEN = self.C_LCYAN = ""
            self.C_LRED = self.C_LMAGENTA = self.C_YELLOW = self.C_WHITE = ""
            self.C_RESET = ""

    def fmt_doc(self, docname: str, color: str) -> str:
        """Format a document label in a consistent, colored style, and return it."""
        return f"{self.C_DGRAY}[{color}{docname}{self.C_DGRAY}]{self.C_RESET}"

    def colorize(self, text: str, color: str) -> str:
        """Wrap a text in a color code and reset suffix and return it."""
        return f"{color}{text}{self.C_RESET}"

    def fmt_step(self, step: int) -> str:
        """Return given compile step number as colorized string"""
        return self.colorize(f"{step:02d}.", self.C_DGRAY)

    def plain(self, msg: str = "", stderr: bool = False) -> None:
        """Print a plain info line (no prefix)."""
        print(msg, flush=True, file=sys.stderr if stderr else sys.stdout)

    def line(self, prefix: str, msg: str, stderr: bool = False) -> None:
        """Print a custom-prefixed line."""
        print(f"{prefix}{msg}", flush=True, file=sys.stderr if stderr else sys.stdout)

    def info_line(self, msg: str, stderr: bool = False) -> None:
        """Print a INFO-prefixed line."""
        print(f"{self.PRETXT_INFO}{msg}", flush=True, file=sys.stderr if stderr else sys.stdout)

    def container_line(self, msg: str, stderr: bool = False) -> None:
        """Print a CONTAINER-prefixed line."""
        print(f"{self.PRETXT_CONTAINER}{msg}", flush=True, file=sys.stderr if stderr else sys.stdout)

    def git_line(self, msg: str, stderr: bool = False) -> None:
        """Print a GIT-prefixed line."""
        print(f"{self.PRETXT_GIT}{msg}", flush=True, file=sys.stderr if stderr else sys.stdout)

    def start_line(self, msg: str, stderr: bool = False) -> None:
        """Print a START-prefixed line."""
        print(f"{self.PRETXT_START}{msg}", flush=True, file=sys.stderr if stderr else sys.stdout)

    def exec_line(self, msg: str, stderr: bool = False) -> None:
        """Print an EXEC-prefixed line."""
        print(f"{self.PRETXT_EXEC}{msg}", flush=True, file=sys.stderr if stderr else sys.stdout)

    def noexec_line(self, msg: str, stderr: bool = False) -> None:
        """Print a NOEXEC-prefixed line."""
        print(f"{self.PRETXT_NOEXEC}{msg}", flush=True, file=sys.stderr if stderr else sys.stdout)

    def deploy_line(self, msg: str, stderr: bool = False) -> None:
        """Print a DEPLOY-prefixed line."""
        print(f"{self.PRETXT_DEPLOY}{msg}", flush=True, file=sys.stderr if stderr else sys.stdout)

    def nodeploy_line(self, msg: str, stderr: bool = False) -> None:
        """Print a NODEPLOY-prefixed line."""
        print(f"{self.PRETXT_NODEPLOY}{msg}", flush=True, file=sys.stderr if stderr else sys.stdout)

    def debug_line(self, msg: str, stderr: bool = False) -> None:
        """Print a DEBUG-prefixed line."""
        print(f"{self.PRETXT_DEBUG}{msg}", flush=True, file=sys.stderr if stderr else sys.stdout)

    def see_line(self, msg: str, stderr: bool = False) -> None:
        """Print a SEE-prefixed line with a path or hint."""
        print(f"{self.PRETXT_SEE}{msg}", flush=True, file=sys.stderr if stderr else sys.stdout)

    def warning_line(self, msg: str, stderr: bool = False) -> None:
        """Print a WARNING-prefixed line."""
        print(f"{self.PRETXT_WARNING}{msg}", flush=True, file=sys.stderr if stderr else sys.stdout)

    def success_line(self, msg: str, stderr: bool = False) -> None:
        """Print a SUCCESS-prefixed line."""
        print(f"{self.PRETXT_SUCCESS}{msg}", flush=True, file=sys.stderr if stderr else sys.stdout)

    def space_line(self, msg: str, stderr: bool = False) -> None:
        """Print an indented continuation/space line."""
        print(f"{self.PRETXT_SPACE}{msg}", flush=True, file=sys.stderr if stderr else sys.stdout)

    # The following will be printed to stderr by default

    def error_line(self, msg: str, stderr: bool = True) -> None:
        """Print an ERROR-prefixed line."""
        print(f"{self.PRETXT_ERROR}{msg}", flush=True, file=sys.stderr if stderr else sys.stdout)

    def fail_line(self, msg: str, stderr: bool = True) -> None:
        """Print a FAIL-prefixed line."""
        print(f"{self.PRETXT_FAIL}{msg}", flush=True, file=sys.stderr if stderr else sys.stdout)

    def abort_line(self, msg: str, stderr: bool = True) -> None:
        """Print an ABORTED-prefixed line."""
        print(f"{self.PRETXT_ABORT}{msg}", flush=True, file=sys.stderr if stderr else sys.stdout)
