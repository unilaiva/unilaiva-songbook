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
        """Init ANSI color codes and prefixes if terminal supports colors."""
        self.use_colors = bool(self.use_colors and self._terminal_supports_colors())
        self._init_colors()

        self.doc_colors = [
            self.C_BROWN, self.C_MAGENTA, self.C_CYAN, self.C_BLUE,
            self.C_YELLOW, self.C_LMAGENTA, self.C_LCYAN, self.C_LBLUE
        ]

        self.PRETXT_DOCKER   = f"{self.C_WHITE}DOCKER   {self.C_RESET}"
        self.PRETXT_GIT      = f"{self.C_WHITE}GIT      {self.C_RESET}"
        self.PRETXT_START    = f"{self.C_GREEN}START    {self.C_RESET}"
        self.PRETXT_EXEC     = f"{self.C_WHITE}EXEC     {self.C_RESET}"
        self.PRETXT_NOEXEC   = f"{self.C_DGRAY}NOEXEC   {self.C_RESET}"
        self.PRETXT_DEPLOY   = f"{self.C_WHITE}DEPLOY   {self.C_RESET}"
        self.PRETXT_NODEPLOY = f"{self.C_DGRAY}NODEPLOY {self.C_RESET}"
        self.PRETXT_DEBUG    = f"{self.C_DGRAY}DEBUG    {self.C_RESET}"
        self.PRETXT_WARNING  = f"{self.C_YELLOW}WARNING  {self.C_RESET}"
        self.PRETXT_ERROR    = f"{self.C_RED}ERROR    {self.C_RESET}"
        self.PRETXT_FAIL     = f"{self.C_LRED}FAIL     {self.C_RESET}"
        self.PRETXT_ABORT    = f"{self.C_LRED}ABORTED  {self.C_RESET}"
        self.PRETXT_SUCCESS  = f"{self.C_LGREEN}SUCCESS  {self.C_RESET}"
        self.PRETXT_SEE      = f"{self.C_DGRAY}SEE      {self.C_RESET}"
        self.PRETXT_SPACE    = f"{self.C_DGRAY}         {self.C_RESET}"


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

    def info(self, msg: str = "") -> None:
        """Print a plain info line (no prefix)."""
        print(msg, flush=True)

    def line(self, prefix: str, msg: str) -> None:
        """Print a custom-prefixed line."""
        print(f"{prefix}{msg}", flush=True)

    def docker_line(self, msg: str) -> None:
        """Print a DOCKER-prefixed line."""
        print(f"{self.PRETXT_DOCKER}{msg}", flush=True)

    def git_line(self, msg: str) -> None:
        """Print a GIT-prefixed line."""
        print(f"{self.PRETXT_GIT}{msg}", flush=True)

    def start_line(self, msg: str) -> None:
        """Print a START-prefixed line."""
        print(f"{self.PRETXT_START}{msg}", flush=True)

    def exec_line(self, msg: str) -> None:
        """Print an EXEC-prefixed line."""
        print(f"{self.PRETXT_EXEC}{msg}", flush=True)

    def noexec_line(self, msg: str) -> None:
        """Print a NOEXEC-prefixed line."""
        print(f"{self.PRETXT_NOEXEC}{msg}", flush=True)

    def deploy_line(self, msg: str) -> None:
        """Print a DEPLOY-prefixed line."""
        print(f"{self.PRETXT_DEPLOY}{msg}", flush=True)

    def nodeploy_line(self, msg: str) -> None:
        """Print a NODEPLOY-prefixed line."""
        print(f"{self.PRETXT_NODEPLOY}{msg}", flush=True)

    def debug_line(self, msg: str) -> None:
        """Print a DEBUG-prefixed line."""
        print(f"{self.PRETXT_DEBUG}{msg}", flush=True)

    def warning_line(self, msg: str) -> None:
        """Print a WARNING-prefixed line."""
        print(f"{self.PRETXT_WARNING}{msg}", flush=True)

    def error_line(self, msg: str) -> None:
        """Print an ERROR-prefixed line."""
        print(f"{self.PRETXT_ERROR}{msg}", flush=True)

    def fail_line(self, msg: str) -> None:
        """Print a FAIL-prefixed line."""
        print(f"{self.PRETXT_FAIL}{msg}", flush=True)

    def abort_line(self, msg: str) -> None:
        """Print an ABORTED-prefixed line."""
        print(f"{self.PRETXT_ABORT}{msg}", flush=True)

    def success_line(self, msg: str) -> None:
        """Print a SUCCESS-prefixed line."""
        print(f"{self.PRETXT_SUCCESS}{msg}", flush=True)

    def see_line(self, msg: str) -> None:
        """Print a SEE-prefixed line with a path or hint."""
        print(f"{self.PRETXT_SEE}{msg}", flush=True)

    def space_line(self, msg: str) -> None:
        """Print an indented continuation/space line."""
        print(f"{self.PRETXT_SPACE}{msg}", flush=True)
