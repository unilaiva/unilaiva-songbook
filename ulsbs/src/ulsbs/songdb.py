# SPDX-FileCopyrightText: 2016-2026 Lari Natri <lari.natri@iki.fi>
# SPDX-License-Identifier: GPL-3.0-or-later

"""
Song/chapter metadata extraction from a TeX tree.

This module parses a main .tex file (preferably already processed with
lilypond-book to get the MIDI files it has produced), recursively follows
\\input and \\include directives, and builds a small in-memory database of the
songbook's metadata.

This file is part of the 'ulsbs' package.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
from pathlib import Path
import re
import unicodedata
from typing import Any, Dict, List, Sequence, Tuple

from .constants import TEX_SUFFIXES


# Data structures
# ===============


@dataclass(slots=True)
class AudioLink:
    """
    A single \\audio[key=X,title=X,pitch=X]{url} invocation.

    Attributes
    ----------
    - url:
        Mandatory argument of \\audio
    - title:
        Optional title for this link
    - key:
        Optional key parameter (musical key, e.g. Am).
    - pitch:
        Optional pitch parameter (ought to define A in Hz).
    """

    url: str
    title: str | None = None
    key: str | None = None
    pitch: str | None = None


@dataclass(slots=True)
class SongInfo:
    """Metadata for a single song.

    Attributes
    ----------
    - title:
        Song title as written in \beginsong{...} (unmodified).
    - title_slug:
        ASCII filename-friendly stem derived from title.
    - number:
        Song number taken from the current songnum counter, if known.
    - options:
        Parsed optional key/value arguments given to \\beginsong[..].
    - tex_file:
        Path to the TeX file where the song is defined.
    - midi_rel_path:
        MIDI file path relative to the main document directory, if detected.
    - midi_abs_path:
        Absolute MIDI file path, if detected and resolvable.
    - order_index:
        Monotonic index reflecting document order across the whole tree.
    - chapter_title:
        Title of the chapter the song belongs to, or None if outside
        any chapter.
    - chapter_slug:
        Normalized chapter slug, or None.
    - audio_links:
        \\audio invocations found inside the song block, in order.
    """

    title: str
    title_slug: str
    number: int | None
    options: Dict[str, str]
    tex_file: Path
    midi_rel_path: Path | None
    midi_abs_path: Path | None
    order_index: int
    chapter_title: str | None
    chapter_slug: str | None
    audio_links: List[AudioLink] = field(default_factory=list)


@dataclass(slots=True)
class ChapterInfo:
    """Metadata for a chapter and its songs."""

    title: str
    slug: str
    tex_file: Path
    songs: List[SongInfo] = field(default_factory=list)
    audio_links: List[AudioLink] = field(default_factory=list)


@dataclass(slots=True)
class BookInfo:
    """
    Metadata about the songbook itself, extracted from \\documentclass
    options and \\renewcommand / \\newcommand definitions.

    All fields default to None and are filled in opportunistically while
    walking the TeX tree. Fields correspond to the key=value options accepted
    by ulsbs-songbook.cls and the LaTeX commands they map to.

    Attributes
    ----------
    - document_class:
        The class name given to \\documentclass{...}.
    - paper:
        Paper size identifier (cls option paper / \\papersize).
    - maintitle:
        Main book title (cls option maintitle / \\mainbooktitle).
    - subtitle:
        Book subtitle (cls option subtitle / \\subbooktitle).
    - subsubtitle:
        Secondary subtitle (cls option subsubtitle / \\subsubbooktitle).
    - motto:
        Book motto (cls option motto / \\bookmotto).
    - wwwlink:
        Website URL (cls option wwwlink / \\bookwebsitelink).
    - wwwqr:
        QR-code image name for website (cls option wwwqr /
        \\bookwebsitelinkqrimage).
    - imprintnote:
        Imprint page footnote (cls option imprintnote /
        \\imprintpagefootnote).
    - author:
        Author/PDF metadata (cls option author / \\pdfauthor).
    - subject:
        Subject/PDF metadata (cls option subject / \\pdfsubject).
    - keywords:
        Keywords/PDF metadata (cls option keywords / \\pdfkeywords).
    - language:
        Document language (cls option language / \\preliminarylanguage).
    - bindingoffset:
        Binding offset dimension (cls option bindingoffset /
        \\ulbindingoffset).
    bookbytext:
        "Book by" attribution text (\\bookbytext).
    """

    document_class: str | None = None
    paper: str | None = None
    maintitle: str | None = None
    subtitle: str | None = None
    subsubtitle: str | None = None
    motto: str | None = None
    wwwlink: str | None = None
    wwwqr: str | None = None
    imprintnote: str | None = None
    author: str | None = None
    subject: str | None = None
    keywords: str | None = None
    language: str | None = None
    bindingoffset: str | None = None
    bookbytext: str | None = None
    audio_links: List[AudioLink] = field(default_factory=list)


# Map from LaTeX command name (without leading backslash) to BookInfo field name.
_BOOK_COMMAND_TO_FIELD: Dict[str, str] = {
    "papersize": "paper",
    "mainbooktitle": "maintitle",
    "subbooktitle": "subtitle",
    "subsubbooktitle": "subsubtitle",
    "bookmotto": "motto",
    "bookwebsitelink": "wwwlink",
    "bookwebsitelinkqrimage": "wwwqr",
    "imprintpagefootnote": "imprintnote",
    "pdfauthor": "author",
    "pdfsubject": "subject",
    "pdfkeywords": "keywords",
    "preliminarylanguage": "language",
    "ulbindingoffset": "bindingoffset",
    "bookbytext": "bookbytext",
}

# Map from \documentclass key=value option name to BookInfo field name.
_BOOK_OPTION_TO_FIELD: Dict[str, str] = {
    "paper": "paper",
    "maintitle": "maintitle",
    "subtitle": "subtitle",
    "subsubtitle": "subsubtitle",
    "motto": "motto",
    "wwwlink": "wwwlink",
    "wwwqr": "wwwqr",
    "imprintnote": "imprintnote",
    "author": "author",
    "subject": "subject",
    "keywords": "keywords",
    "language": "language",
    "bindingoffset": "bindingoffset",
}


@dataclass(slots=True)
class SongbookData:
    """Container for all chapters and songs discovered in a TeX tree."""

    book_info: BookInfo
    chapters: List[ChapterInfo]
    songs_without_chapter: List[SongInfo]

    def to_json_file(self, dest: Path, *, indent: int = 2) -> None:
        """
        Write the database to dest as a JSON file.

        Uses only the Python standard library.  Path objects are serialised as
        POSIX strings; None values are preserved as JSON null.

        Parameters
        ----------
        - dest:
            Output file path.  Parent directories must already exist.
        - indent:
            JSON indentation level (default 2).
        """

        def _default(obj: Any) -> Any:
            if isinstance(obj, Path):
                return obj.as_posix()
            raise TypeError("Object of type %s is not JSON-serialisable" % type(obj).__name__)

        raw = asdict(self)
        dest.write_text(json.dumps(raw, default=_default, indent=indent, ensure_ascii=False), encoding="utf-8")


# Helpers
# =======


_INPUT_MACROS = ("\\input", "\\include")
_CHAPTER_MACROS = ("\\mainchapter", "\\chapter", "\\songchapter")


def _strip_tex_commands(text: str) -> str:
    """Remove simple TeX commands from a short piece of text.

    This is *not* a general TeX cleaner; it is just enough to derive
    filename-friendly slugs from chapter and song titles.
    """

    # Line breaks like \\ -> space
    text = text.replace("\\\\", " ")

    # Remove common LaTeX commands and their optional args, keep inner text
    # e.g. \textbf{Foo} -> "Foo".
    text = re.sub(r"\\[a-zA-Z]+\*?(?:\[[^\]]*\])?\{([^}]*)\}", r"\1", text)

    # Drop any remaining backslash-starting control words
    text = re.sub(r"\\[a-zA-Z]+\*?", "", text)

    return text


def _slugify(text: str, *, default: str) -> str:
    """
    Return an ASCII slug suitable for filenames/dirnames.

    - Lowercases
    - Converts accented characters to their base forms
    - Replaces whitespace and punctuation with -
    - Collapses multiple dashes and strips leading/trailing dashes
    """

    cleaned = _strip_tex_commands(text)
    cleaned = unicodedata.normalize("NFKD", cleaned)
    cleaned = cleaned.encode("ascii", "ignore").decode("ascii")
    cleaned = cleaned.lower()
    cleaned = re.sub(r"[^a-z0-9]+", "-", cleaned)
    cleaned = cleaned.strip("-")
    return cleaned or default


def _parse_braced_argument(src: str, start: int) -> Tuple[str, int]:
    """
    Parse a single {...} argument starting at start.

    Returns (content, next_index_after_argument).
    Raises ValueError if the braces are unbalanced.
    """

    if start >= len(src) or src[start] != "{":
        raise ValueError("Expected '{' at position %d" % start)
    depth = 0
    i = start
    out_chars: List[str] = []
    while i < len(src):
        ch = src[i]
        if ch == "{":
            if depth > 0:
                out_chars.append(ch)
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return ("".join(out_chars), i + 1)
            out_chars.append(ch)
        else:
            out_chars.append(ch)
        i += 1
    raise ValueError("Unterminated '{' starting at %d" % start)


def _parse_optional_bracket_argument(src: str, start: int) -> Tuple[str | None, int]:
    """
    Parse an optional [ ... ] argument starting at start.

    If there is no [ at start, returns (None, start).
    Nested brackets are handled.
    """

    if start >= len(src) or src[start] != "[":
        return None, start
    depth = 0
    i = start
    out_chars: List[str] = []
    while i < len(src):
        ch = src[i]
        if ch == "[":
            if depth > 0:
                out_chars.append(ch)
            depth += 1
        elif ch == "]":
            depth -= 1
            if depth == 0:
                return "".join(out_chars), i + 1
            out_chars.append(ch)
        else:
            out_chars.append(ch)
        i += 1
    raise ValueError("Unterminated '[' starting at %d" % start)


def _parse_beginsong_header(src: str, start: int) -> Tuple[str, Dict[str, str], int]:
    """
    Parse \\beginsong{Title}[options] starting at start.

    Returns (title, options_dict, next_index).
    """

    # Skip the macro name itself, which is known by the caller
    i = start
    # Consume macro token \\beginsong
    assert src.startswith("\\beginsong", i)
    i += len("\\beginsong")

    # Skip whitespace
    while i < len(src) and src[i].isspace():
        i += 1

    # Required {title}
    if i >= len(src) or src[i] != "{":
        raise ValueError("\\beginsong without {title} at position %d" % i)
    title, i = _parse_braced_argument(src, i)

    # Skip whitespace
    while i < len(src) and src[i].isspace():
        i += 1

    # Optional [options]
    opts_raw, i = _parse_optional_bracket_argument(src, i)
    options: Dict[str, str] = {}
    if opts_raw:
        options = _parse_keyval_options(opts_raw)

    return title, options, i


def _parse_keyval_options(raw: str) -> Dict[str, str]:
    """
    Parse a simple comma-separated key=val list used in \\beginsong.

    Values may use braces, e.g. by={Someone}.  Commas inside braces are
    preserved and do not split options.
    """

    result: Dict[str, str] = {}
    i = 0
    n = len(raw)
    while i < n:
        # Skip whitespace and commas
        while i < n and raw[i] in " \t\r\n,":
            i += 1
        if i >= n:
            break

        # Parse key
        key_start = i
        while i < n and re.match(r"[A-Za-z0-9_*]", raw[i]):
            i += 1
        key = raw[key_start:i].strip()
        if not key:
            # Skip junk until next comma
            while i < n and raw[i] != ",":
                i += 1
            continue

        # Skip whitespace
        while i < n and raw[i].isspace():
            i += 1

        if i >= n or raw[i] != "=":
            # Flag-style option without explicit value
            result[key] = ""
            continue
        i += 1  # skip '='

        # Skip whitespace before value
        while i < n and raw[i].isspace():
            i += 1

        # Parse value
        if i < n and raw[i] == "{":
            val, i = _parse_braced_argument(raw, i)
        else:
            # Read until next comma
            val_start = i
            while i < n and raw[i] != ",":
                i += 1
            val = raw[val_start:i].strip()

        result[key] = val
    return result


def _resolve_include(name: str, current_file: Path, search_paths: Sequence[Path]) -> Path | None:
    """Resolve an \\input / \\include target to an actual file.

    The search order is:
      1. Path relative to the current file directory
      2. Each directory in search_paths (as-is and with common TeX suffixes
         appended)
    """

    candidates: List[Path] = []
    name = name.strip()
    if not name:
        return None

    # If the name already has an extension, try it as-is first
    explicit = Path(name)

    # Skip ulsbs .ly files as they contain no info we need.
    if explicit.suffix == ".ly" and re.match(r"ulsbs-(?:include|internal)", explicit.stem):
        return None

    # Try the given name as-is in current dir first
    rel_current = (current_file.parent / explicit).resolve()
    candidates.append(rel_current)

    # Then try common TeX suffixes in current dir
    for suffix in TEX_SUFFIXES:
        if explicit.suffix != suffix:
            candidates.append((current_file.parent / (name + suffix)).resolve())

    # Then loop through given search paths
    for base in search_paths:
        base = base.resolve()
        # First with the name as-is
        candidates.append((base / explicit).resolve())
        # And then with common TeX suffixes
        for suffix in TEX_SUFFIXES:
            if explicit.suffix != suffix:
                candidates.append((base / (name + suffix)).resolve())

    for cand in candidates:
        if cand.is_file():
            return cand
    return None


def _parse_audio_command(src: str, start: int) -> Tuple[AudioLink | None, int]:
    r"""
    Parse \audio{url}[key=X,title=X,pitch=X] starting at start.

    start must point to the \ of \audio.

    Returns (AudioLink, next_index) on success, or (None, start) on failure.
    The optional bracket argument may contain key, title and/or pitch in any
    order.
    """

    i = start
    assert src.startswith("\\audio", i)
    i += len("\\audio")

    # Skip whitespace
    while i < len(src) and src[i].isspace():
        i += 1

    if i >= len(src) or src[i] != "{":
        return None, start

    try:
        url, i = _parse_braced_argument(src, i)
    except ValueError:
        return None, start

    # Skip whitespace before optional [...]
    j = i
    while j < len(src) and src[j].isspace():
        j += 1

    opts_raw: str | None = None
    if j < len(src) and src[j] == "[":
        try:
            opts_raw, i = _parse_optional_bracket_argument(src, j)
        except ValueError:
            pass

    key: str | None = None
    title: str | None = None
    pitch: str | None = None
    if opts_raw is not None:
        kv = _parse_keyval_options(opts_raw)
        key = kv.get("key") or None
        title = kv.get("title") or None
        pitch = kv.get("pitch") or None

    return AudioLink(url=url.strip(), key=key, title=title, pitch=pitch), i


def _collect_audio_links_from_block(raw_block: str) -> List[AudioLink]:
    """Return all \\audio invocations found inside raw_block, in order."""

    links: List[AudioLink] = []
    i = 0
    n = len(raw_block)
    while i < n:
        idx = raw_block.find("\\audio", i)
        if idx == -1:
            break
        # Make sure it's not e.g. \audiolink or similar
        after = idx + len("\\audio")
        if after < n and raw_block[after].isalpha():
            i = after
            continue
        link, i = _parse_audio_command(raw_block, idx)
        if link is not None:
            links.append(link)
        else:
            i = idx + len("\\audio")
    return links


def _find_midi_in_song_block(raw_song: str, doc_root: Path) -> Tuple[Path | None, Path | None]:
    """
    Infer the MIDI file path for a song block, if any.

    Looks for a substring produced by lilypond-book containing lilypondbook and
    an \\input{...-systems.tex} call.
    """

    if "lilypondbook" not in raw_song:
        return None, None

    try:
        after = raw_song.split("lilypondbook", 1)[1]
        after_input = after.split("\\input{", 1)[1]
        input_arg = after_input.split("}", 1)[0].strip()
    except Exception:
        return None, None

    if not input_arg:
        return None, None

    # Derive MIDI filename from the "-systems.tex" helper filename
    midi_rel_str = input_arg.split("-systems.tex", 1)[0] + ".midi"
    midi_rel = Path(midi_rel_str)
    midi_abs = (doc_root / midi_rel).resolve()
    if not midi_abs.is_file():
        return midi_rel, None
    return midi_rel, midi_abs


# Main walker
# ===========


def _apply_book_field(book_info: BookInfo, field_name: str, value: str) -> None:
    """Set field_name on book_info to value, stripping outer whitespace."""
    object.__setattr__(book_info, field_name, value.strip())


def build_song_database(processed_tex: Path, include_search_paths: Sequence[Path]) -> SongbookData:
    """
    Parse processed_tex and all its inputs into a SongbookData class.

    Parameters
    ----------
    - processed_tex:
        Main LaTeX document, typically already processed with lilypond-book.
    - include_search_paths:
        Directories where \\input / \\include should be resolved.

    Returns SongbookData (Complete chapter + song information for this document).
    """

    processed_tex = processed_tex.resolve()
    if not processed_tex.is_file():
        raise FileNotFoundError(processed_tex)

    doc_root = processed_tex.parent
    search_paths = [p.resolve() for p in include_search_paths]

    book_info = BookInfo()
    chapters: List[ChapterInfo] = []
    songs_without_chapter: List[SongInfo] = []
    visited: set[Path] = set()

    current_chapter: ChapterInfo | None = None
    current_songnum: int | None = None
    current_song_in_progress: bool | None = None
    order_counter = 0

    def add_song(
        *,
        title: str,
        options: Dict[str, str],
        tex_file: Path,
        raw_block: str,
    ) -> None:
        nonlocal current_songnum, order_counter

        title_slug = _slugify(title, default="song")
        number = current_songnum
        if current_songnum is None:
            number = None
        else:
            current_songnum += 1

        midi_rel, midi_abs = _find_midi_in_song_block(raw_block, doc_root)
        audio_links = _collect_audio_links_from_block(raw_block)

        order_counter += 1
        song = SongInfo(
            title=title,
            title_slug=title_slug,
            number=number,
            options=options,
            tex_file=tex_file,
            midi_rel_path=midi_rel,
            midi_abs_path=midi_abs,
            order_index=order_counter,
            chapter_title=current_chapter.title if current_chapter else None,
            chapter_slug=current_chapter.slug if current_chapter else None,
            audio_links=audio_links,
        )

        if current_chapter is None:
            songs_without_chapter.append(song)
        else:
            current_chapter.songs.append(song)

    def process_file(path: Path, *, is_root: bool = False) -> None:  # noqa: C901
        nonlocal current_chapter, current_songnum, current_song_in_progress, order_counter

        path = path.resolve()
        if path in visited:
            return
        visited.add(path)

        try:
            src = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            # Fallback with replacement to stay robust
            src = path.read_text(encoding="utf-8", errors="replace")

        i = 0
        n = len(src)
        while i < n:
            ch = src[i]
            if ch != "\\":
                i += 1
                continue

            # \documentclass (root file only)
            if is_root and src.startswith("\\documentclass", i):
                i += len("\\documentclass")
                while i < n and src[i].isspace():
                    i += 1
                # Optional [key=val,...] options
                opts_raw, i = _parse_optional_bracket_argument(src, i)
                while i < n and src[i].isspace():
                    i += 1
                # Required {classname}
                if i < n and src[i] == "{":
                    try:
                        classname, i = _parse_braced_argument(src, i)
                        book_info.document_class = classname.strip()
                    except ValueError:
                        pass
                if opts_raw:
                    for opt_key, opt_val in _parse_keyval_options(opts_raw).items():
                        field_name = _BOOK_OPTION_TO_FIELD.get(opt_key)
                        if field_name is not None:
                            _apply_book_field(book_info, field_name, opt_val)
                continue

            # \renewcommand / \newcommand / \providecommand for known book macros
            for cmd_macro in ("\\renewcommand", "\\newcommand", "\\providecommand"):
                if src.startswith(cmd_macro, i):
                    j = i + len(cmd_macro)
                    while j < n and src[j].isspace():
                        j += 1
                    # Argument can be \macroname or {\macroname}
                    macro_name: str | None = None
                    if j < n and src[j] == "{":
                        # {\macroname}
                        if j + 1 < n and src[j + 1] == "\\":
                            try:
                                inner, j2 = _parse_braced_argument(src, j)
                                macro_name = inner.strip().lstrip("\\")
                                j = j2
                            except ValueError:
                                pass
                    elif j < n and src[j] == "\\":
                        # \macroname (unbraced)
                        j += 1  # skip leading backslash
                        name_start = j
                        while j < n and src[j].isalpha():
                            j += 1
                        macro_name = src[name_start:j]
                    if macro_name and macro_name in _BOOK_COMMAND_TO_FIELD:
                        # Skip optional [nargs] or [nargs][default]
                        while j < n and src[j].isspace():
                            j += 1
                        if j < n and src[j] == "[":
                            _, j = _parse_optional_bracket_argument(src, j)
                            while j < n and src[j].isspace():
                                j += 1
                            if j < n and src[j] == "[":
                                _, j = _parse_optional_bracket_argument(src, j)
                                while j < n and src[j].isspace():
                                    j += 1
                        # The replacement text
                        if j < n and src[j] == "{":
                            try:
                                value, j = _parse_braced_argument(src, j)
                                field_name = _BOOK_COMMAND_TO_FIELD[macro_name]
                                _apply_book_field(book_info, field_name, value)
                                i = j
                            except ValueError:
                                pass
                    break  # matched one of the cmd_macros prefixes

            # Try inputs/includes
            if any(src.startswith(m, i) for m in _INPUT_MACROS):
                if src.startswith("\\input", i):
                    i += len("\\input")
                else:
                    i += len("\\include")

                # Skip whitespace
                while i < n and src[i].isspace():
                    i += 1
                if i >= n or src[i] != "{":
                    continue
                try:
                    target, i = _parse_braced_argument(src, i)
                except ValueError:
                    continue
                target_path = _resolve_include(target, path, search_paths)
                if target_path is not None:
                    process_file(target_path)
                continue


            # Chapters
            if any(src.startswith(m, i) for m in _CHAPTER_MACROS):
                if src.startswith("\\mainchapter", i):
                    macro = "\\mainchapter"
                elif src.startswith("\\songchapter", i):
                    macro = "\\songchapter"
                else:
                    macro = "\\chapter"
                i += len(macro)

                # For mainchapter, the syntax is
                #   \mainchapter[short]{long}{colorname}
                # For chapter/songchapter we only care about the first {title}.

                # Optional [..]
                while i < n and src[i].isspace():
                    i += 1
                if i < n and src[i] == "[":
                    _, i = _parse_optional_bracket_argument(src, i)
                    while i < n and src[i].isspace():
                        i += 1

                if i >= n or src[i] != "{":
                    continue
                try:
                    title, i = _parse_braced_argument(src, i)
                except ValueError:
                    continue

                title = title.strip()
                slug = _slugify(title, default="chapter")
                chap = ChapterInfo(title=title, slug=slug, tex_file=path)
                chapters.append(chap)
                current_chapter = chap
                # Do *not* reset songnum; we follow whatever \setcounter does
                continue

            # songnum counter
            if src.startswith("\\setcounter", i):
                i += len("\\setcounter")
                while i < n and src[i].isspace():
                    i += 1
                if i >= n or src[i] != "{":
                    continue
                try:
                    counter_name, i2 = _parse_braced_argument(src, i)
                except ValueError:
                    i += 1
                    continue
                counter_name = counter_name.strip()
                i = i2
                while i < n and src[i].isspace():
                    i += 1
                if i >= n or src[i] != "{":
                    continue
                try:
                    val_str, i = _parse_braced_argument(src, i)
                except ValueError:
                    continue
                if counter_name == "songnum":
                    try:
                        current_songnum = int(val_str.strip())
                    except ValueError:
                        current_songnum = None
                continue

            # \audio outside a song block
            if src.startswith("\\audio", i):
                audio_link, i_after = _parse_audio_command(src, i)
                if audio_link is not None:
                    if current_song_in_progress is None:
                        # Outside any song: attach to chapter or book
                        if current_chapter is not None:
                            current_chapter.audio_links.append(audio_link)
                        else:
                            book_info.audio_links.append(audio_link)
                    # If inside a song block the link is collected via
                    # _collect_audio_links_from_block after \endsong.
                    i = i_after
                    continue
                i += 1
                continue

            # Songs
            if src.startswith("\\beginsong", i):
                song_start = i
                try:
                    title, options, i_after_header = _parse_beginsong_header(src, i)
                except ValueError:
                    i += len("\\beginsong")
                    continue

                # Find matching \endsong from after the header
                end_idx = src.find("\\endsong", i_after_header)
                if end_idx == -1:
                    end_idx = n
                raw_block = src[song_start:end_idx]

                current_song_in_progress = True
                add_song(title=title.strip(), options=options, tex_file=path, raw_block=raw_block)
                current_song_in_progress = None

                i = end_idx + len("\\endsong") if end_idx < n else n
                continue

            # Default: skip this backslash and continue
            i += 1

    process_file(processed_tex, is_root=True)

    return SongbookData(book_info=book_info, chapters=chapters, songs_without_chapter=songs_without_chapter)
