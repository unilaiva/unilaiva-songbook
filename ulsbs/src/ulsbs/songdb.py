# SPDX-FileCopyrightText: 2016-2026 Lari Natri <lari.natri@iki.fi>
# SPDX-License-Identifier: GPL-3.0-or-later

"""
Song/chapter metadata extraction from a TeX tree.

This module parses a main .tex file (preferably already processed with
lilypond-book to get the MIDI files it has produced), recursively follows
\\input and \\include directives, and builds a small in-memory database of the
songbook's metadata.

This file is part of the 'ulsbs' package.

JSON schema
-----------

The JSON produced by 'SongbookData.to_json_file()' conforms to the
following JSON Schema (draft-07):

    {
      "$schema": "http://json-schema.org/draft-07/schema#",
      "title": "ulsbs SongbookData",
      "type": "object",
      "required": [
        "book_info",
        "chapters",
        "songs_without_chapter",
        "source_file_relative",
        "total_songs",
        "creation_time"
      ],
      "properties": {
        "book_info": {"$ref": "#/definitions/BookInfo"},
        "chapters": {
          "type": "array",
          "items": {"$ref": "#/definitions/ChapterInfo"}
        },
        "songs_without_chapter": {
          "type": "array",
          "items": {"$ref": "#/definitions/SongInfo"}
        },
        "source_file_relative": {
          "type": "string",
          "description": "Path to the main TeX source file relative to the main document directory (POSIX string)"
        },
        "total_songs": {
          "type": "integer",
          "minimum": 0
        },
        "creation_time": {
          "type": "string",
          "description": "ISO 8601 timestamp when this database was created"
        }
      },
      "additionalProperties": false,
      "definitions": {
        "AudioLink": {
          "type": "object",
          "required": ["url"],
          "properties": {
            "url": {"type": "string"},
            "title": {"type": ["string", "null"]},
            "key": {"type": ["string", "null"]},
            "pitch": {"type": ["string", "null"]}
          },
          "additionalProperties": false
        },
        "Translation": {
          "type": "object",
          "required": [
            "language",
            "lyrics",
            "lyrics_plain_lowercase"
          ],
          "properties": {
            "language": {"type": ["string", "null"]},
            "lyrics": {
              "type": "array",
              "items": {
                "type": "array",
                "items": {"type": "string"},
                "description": "One verse as an array of translation lines"
              },
              "description": "Structured translated lyrics as [verses][lines] of plain text"
            },
            "lyrics_plain_lowercase": {
              "type": "string",
              "description": "Lowercased plain-text translated lyrics with \\n between lines and \\n\\n between verses"
            }
          },
          "additionalProperties": false
        },
        "BookInfo": {
          "type": "object",
          "required": [
            "document_class",
            "paper",
            "maintitle",
            "subtitle",
            "subsubtitle",
            "motto",
            "variant",
            "wwwlink",
            "wwwqr",
            "imprintnote",
            "author",
            "subject",
            "keywords",
            "language",
            "bindingoffset",
            "bookbynote",
            "audio_links"
          ],
          "properties": {
            "document_class": {"type": ["string", "null"]},
            "paper": {"type": ["string", "null"]},
            "maintitle": {"type": ["string", "null"]},
            "subtitle": {"type": ["string", "null"]},
            "subsubtitle": {"type": ["string", "null"]},
            "motto": {"type": ["string", "null"]},
            "variant": {"type": ["string", "null"]},
            "wwwlink": {"type": ["string", "null"]},
            "wwwqr": {"type": ["string", "null"]},
            "imprintnote": {"type": ["string", "null"]},
            "author": {"type": ["string", "null"]},
            "subject": {"type": ["string", "null"]},
            "keywords": {"type": ["string", "null"]},
            "language": {"type": ["string", "null"]},
            "bindingoffset": {"type": ["string", "null"]},
            "bookbynote": {"type": ["string", "null"]},
            "audio_links": {
              "type": "array",
              "items": {"$ref": "#/definitions/AudioLink"}
            }
          },
          "additionalProperties": false
        },
        "ChapterInfo": {
          "type": "object",
          "required": ["title", "slug", "source_file_relative", "songs", "audio_links"],
          "properties": {
            "title": {"type": "string"},
            "slug": {"type": "string"},
            "source_file_relative": {
              "type": "string",
              "description": "Path to the TeX source file relative to the main document directory (POSIX string)"
            },
            "songs": {
              "type": "array",
              "items": {"$ref": "#/definitions/SongInfo"}
            },
            "audio_links": {
              "type": "array",
              "items": {"$ref": "#/definitions/AudioLink"}
            }
          },
          "additionalProperties": false
        },
        "SongInfo": {
          "type": "object",
          "required": [
            "title",
            "title_slug",
            "number",
            "options",
            "source_file_relative",
            "midi_compile_file_relative",
            "order_index",
            "chapter_title",
            "chapter_slug",
            "alt_titles",
            "audio_links",
            "lyrics",
            "lyrics_plain_lowercase",
            "translations"
          ],
          "properties": {
            "title": {"type": "string"},
            "title_slug": {"type": "string"},
            "number": {"type": ["integer", "null"]},
            "options": {
              "type": "object",
              "additionalProperties": {"type": "string"}
            },
            "source_file_relative": {
              "type": "string",
              "description": "Path to the TeX source file where the song is defined, relative to the main document directory (POSIX string)"
            },
            "midi_compile_file_relative": {
              "type": ["string", "null"],
              "description": "MIDI file path in the compile tree, relative to the main document directory (POSIX string)"
            },
            "midi_result_file_relative": {
              "type": ["string", "null"],
              "description": "MIDI result file path relative to the global result directory (POSIX string)"
            },
            "audio_result_file_relative": {
              "type": ["string", "null"],
              "description": "Audio result file path relative to the global result directory (POSIX string)"
            },
            "order_index": {
              "type": "integer",
              "minimum": 1,
              "description": "Monotonic index reflecting document order"
            },
            "chapter_title": {"type": ["string", "null"]},
            "chapter_slug": {"type": ["string", "null"]},
            "alt_titles": {
              "type": "array",
              "items": {"type": "string"}
            },
            "audio_links": {
              "type": "array",
              "items": {"$ref": "#/definitions/AudioLink"}
            },
            "lyrics": {
              "type": ["array", "null"],
              "items": {
                "type": "array",
                "items": {"type": "string"},
                "description": "One verse as an array of lyric lines"
              },
              "description": "Structured lyrics as [verses][lines] of plain text"
            },
            "lyrics_plain_lowercase": {
              "type": ["string", "null"],
              "description": "Lowercased plain-text lyrics with \n between lines and \n\n between verses"
            },
            "translations": {
              "type": "array",
              "items": {"$ref": "#/definitions/Translation"}
            }
          },
          "additionalProperties": false
        }
      }
    }
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
from datetime import datetime, timezone
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
class Translation:
    """One translated lyrics block for a song.

    Attributes
    ----------
    - language:
        Optional language code (e.g. "en"), taken from the optional
        argument to the translation environment or macro and lowercased.
    - lyrics:
        Plain-text translated lyrics structured as verses and lines.
    - lyrics_plain_lowercase:
        Lowercased plain-text translated lyrics with verse and line breaks
        encoded as newlines. Intended for case-insensitive search.
    """

    language: str | None
    lyrics: List[List[str]]
    lyrics_plain_lowercase: str


@dataclass(slots=True)
class SongInfo:
    """Metadata for a single song.

    Attributes
    ----------
    - title:
        Primary song title (the first part before any ``\\`` line breaks).
    - title_slug:
        ASCII filename-friendly stem derived from the primary title.
    - number:
        Song number taken from the current songnum counter, if known.
    - options:
        Parsed optional key/value arguments given to \\beginsong[..].
    - source_file_relative:
        Path to the TeX file where the song is defined, relative to the main document directory.
    - midi_compile_file_relative:
        MIDI file path in the compile tree, relative to the main document directory, if detected.
    - midi_result_file_relative:
        Path to the MIDI file in the result directory, relative to the global result directory.
    - audio_result_file_relative:
        Path to the audio file in the result directory, relative to the global result directory.
    - order_index:
        Monotonic index reflecting document order across the whole tree.
    - chapter_title:
        Title of the chapter the song belongs to, or None if outside
        any chapter.
    - chapter_slug:
        Normalized chapter slug, or None.
    - alt_titles:
        Alternative titles extracted from subsequent ``\\``-separated parts
        of the ``\beginsong{...}`` title, if any.
    - audio_links:
        \\audio invocations found inside the song block, in order.
    - lyrics:
        Plain-text lyrics structured as verses and lines.
    - lyrics_plain_lowercase:
        Lowercased plain-text lyrics with verse and line breaks encoded as
        newlines. Intended for case-insensitive search.
    - translations:
        Zero or more translated lyric blocks, each with an optional
        language code and lyrics structured as verses and lines.
    """

    title: str
    title_slug: str
    number: int | None
    options: Dict[str, str]
    source_file_relative: Path
    midi_compile_file_relative: Path | None
    order_index: int
    chapter_title: str | None
    chapter_slug: str | None
    midi_result_file_relative: Path | None = None
    audio_result_file_relative: Path | None = None
    alt_titles: List[str] = field(default_factory=list)
    audio_links: List[AudioLink] = field(default_factory=list)
    lyrics: List[List[str]] | None = None
    lyrics_plain_lowercase: str | None = None
    translations: List[Translation] = field(default_factory=list)

    def set_midi_result_file_relative(self, path: Path) -> None:
        self.midi_result_file_relative = path

    def set_audio_result_file_relative(self, path: Path) -> None:
        self.audio_result_file_relative = path


@dataclass(slots=True)
class ChapterInfo:
    """Metadata for a chapter and its songs."""

    title: str
    slug: str
    source_file_relative: Path
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
        Paper size identifier (cls option paper / \\ulPapersize).
    - maintitle:
        Main book title (cls option maintitle / \\ulMainBookTitle).
    - subtitle:
        Book subtitle (cls option subtitle / \\ulSubBookTitle).
    - subsubtitle:
        Secondary subtitle (cls option subsubtitle / \\ulSubSubBookTitle).
    - motto:
        Book motto (cls option motto / \\ulBookMotto).
    - wwwlink:
        Website URL (cls option wwwlink / \\ulBookWebsiteLink).
    - wwwqr:
        QR-code image name for website (cls option wwwqr /
        \\ulBookWebsiteLinkQrImage).
    - imprintnote:
        Imprint page footnote (cls option imprintnote /
        \\ulImprintPageFootnote).
    - author:
        Author/PDF metadata (cls option author / \\ulBookAuthor).
    - subject:
        Subject/PDF metadata (cls option subject / \\ulBookSubject).
    - keywords:
        Keywords/PDF metadata (cls option keywords / \\ulBookKeywords).
    - language:
        Document language (cls option language / \\ulPreliminaryLanguage).
    - bindingoffset:
        Binding offset dimension (cls option bindingoffset /
        \\ulBindingOffset).
    - bookbynote:
        "Book by" attribution text (\\ulBookByText).
    """

    document_class: str | None = None
    paper: str | None = None
    maintitle: str | None = None
    subtitle: str | None = None
    subsubtitle: str | None = None
    motto: str | None = None
    variant: str | None = "unknown"  # not parsed, but given to build_song_database()
    wwwlink: str | None = None
    wwwqr: str | None = None
    imprintnote: str | None = None
    author: str | None = None
    subject: str | None = None
    keywords: str | None = None
    language: str | None = None
    bindingoffset: str | None = None
    bookbynote: str | None = None
    audio_links: List[AudioLink] = field(default_factory=list)


# Map from LaTeX command name (without leading backslash) to BookInfo field name.
_BOOK_COMMAND_TO_FIELD: Dict[str, str] = {
    "ulPapersize": "paper",
    "ulMainBookTitle": "maintitle",
    "ulSubBookTitle": "subtitle",
    "ulSubSubBookTitle": "subsubtitle",
    "ulBookMotto": "motto",
    "ulBookWebsiteLink": "wwwlink",
    "ulBookWebsiteLinkQrImage": "wwwqr",
    "ulImprintPageFootnote": "imprintnote",
    "ulBookAuthor": "author",
    "ulBookSubject": "subject",
    "ulBookKeywords": "keywords",
    "ulPreliminaryLanguage": "language",
    "ulBindingOffset": "bindingoffset",
    "ulBookByText": "bookbynote",
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

# NOTE: not used currently
_BOOK_TITLE_FIELDS: set[str] = {"maintitle", "subtitle", "subsubtitle", "motto"}


@dataclass(slots=True)
class SongbookData:
    """Container for all chapters and songs discovered in a TeX tree.

    Attributes
    ----------
    - book_info:
        Global metadata about the songbook.
    - chapters:
        Chapters discovered in the TeX tree, in document order.
    - songs_without_chapter:
        Songs that are not inside any chapter.
    - source_file_relative:
        Path to the main TeX file for this songbook, relative to the main document directory.
    - total_songs:
        Total number of songs discovered across the entire document tree.
        This matches the highest order_index assigned to any song.
    - creation_time:
        ISO 8601 timestamp when this database instance was created.
    """

    book_info: BookInfo
    chapters: List[ChapterInfo]
    songs_without_chapter: List[SongInfo]
    source_file_relative: Path
    total_songs: int
    creation_time: str

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
        dest.write_text(
            json.dumps(raw, default=_default, indent=indent, ensure_ascii=False), encoding="utf-8"
        )


# Helpers
# =======


_INPUT_MACROS = ("\\input", "\\include")
_CHAPTER_MACROS = ("\\ulMainChapter", "\\chapter", "\\songchapter")

# Macros whose braced argument should be preserved in lyrics (name without
# leading backslash). For these, the macro name and braces are stripped but
# the inner text is kept.
_LYRICS_TEXT_MACROS_KEEP_ARG: set[str] = {"text", "textit", "emph"}


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


def _tex_to_plain_text(text: str) -> str:
    """Replace simple TeX accidentals with Unicode symbols and strip TeX markup.

    - \\flt and \\shrp are converted to ♭ and ♯
    - TeX comments (%) are removed (but \\% is kept as a literal %)
    - TeX macros are stripped; their mandatory {...} arguments are kept,
      except when they contain only a TeX length (e.g. 0.5pt, 2ex)
    - Optional arguments [...] are discarded
    - All braces/brackets and control sequences are removed
    - All newline styles are normalized and whitespace collapses to a single space
    """

    # 1. Replace music accidentals
    text = re.sub(r"\\flt(?:\{\})?", "♭", text)
    text = re.sub(r"\\shrp(?:\{\})?", "♯", text)

    # 2. Remove TeX comments: % to end-of-line, except when escaped as \%
    text = re.sub(r"(?<!\\)%[^\r\n]*", "", text)

    # 3. Normalize all newline styles to a space
    text = re.sub(r"[\r\n]+", " ", text)

    # 4. Replace macros with mandatory args by just their arg contents
    length_re = re.compile(
        r"""
        ^\s*
        [+-]?(
            (?:\d+(?:\.\d*)?)  # 1, 1., 1.23
            |
            (?:\.\d+)          # .5
        )
        \s*
        (?:pt|bp|in|cm|mm|pc|dd|cc|sp|ex|em|mu)
        \s*$
        """,
        re.IGNORECASE | re.VERBOSE,
    )

    def _macro_with_args_repl(match: re.Match) -> str:
        braces = match.group("braces")
        if not braces:
            return " "
        contents = re.findall(r"\{([^}]*)\}", braces)
        # Keep non-empty args that are not pure TeX lengths
        kept = [c.strip() for c in contents if c.strip() and not length_re.match(c)]
        return " ".join(kept) if kept else " "

    macro_with_args_re = re.compile(
        r"""
        \\[A-Za-z]+                    # command name
        (?:\s*\[[^\]]*\])?             # optional argument [ ... ], discarded
        (?P<braces>(?:\s*\{[^}]*\})+)  # one or more mandatory { ... } args
        """,
        re.VERBOSE,
    )
    text = macro_with_args_re.sub(_macro_with_args_repl, text)

    # 5. Convert escaped percent to literal percent
    text = text.replace(r"\%", "%")

    # 6. Drop remaining control sequences without mandatory args (e.g. \foo, \\, \&)
    text = re.sub(r"\\[A-Za-z]+|\\.", " ", text)

    # 7. Drop any remaining braces/brackets
    text = re.sub(r"[{}\[\]]", "", text)

    # 8. Collapse all runs of whitespace to a single space
    text = re.sub(r"\s+", " ", text).strip()

    return text


def _unescape_tex_url(text: str) -> str:
    """Undo simple TeX escaping used inside URLs.

    Currently this only normalises ``\\%`` back to a literal ``%``.
    """

    return text.replace(r"\%", "%")


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


def _resolve_documentclass(
    classname: str, current_file: Path, search_paths: Sequence[Path]
) -> Path | None:
    """Resolve a \\documentclass{...} argument to a ``.cls`` file.

    The search order is:
      1. Path relative to the current file directory
      2. Each directory in search_paths
    """

    name = classname.strip()
    if not name:
        return None

    explicit = Path(name)
    candidates: List[Path] = []

    if explicit.suffix:
        # Name already includes an extension (e.g. .cls)
        candidates.append((current_file.parent / explicit).resolve())
        for base in search_paths:
            candidates.append((base.resolve() / explicit).resolve())
    else:
        explicit_cls = explicit.with_suffix(".cls")
        candidates.append((current_file.parent / explicit_cls).resolve())
        for base in search_paths:
            candidates.append((base.resolve() / explicit_cls).resolve())

    for cand in candidates:
        if cand.is_file():
            return cand
    return None


def _parse_audio_command(src: str, start: int) -> Tuple[AudioLink | None, int]:
    """
    Parse \\audio invocations starting at *start*.

    Supported forms are::

        \audio{url}[key=...,title=...,pitch=...]
        \audio[key=...,title=...,pitch=...]{url}

    *start* must point to the \\ of \\audio.

    Returns (AudioLink, next_index) on success, or (None, start) on
    failure. The optional bracket argument may contain key, title
    and/or pitch in any order.
    """

    i = start
    assert src.startswith("\\audio", i)
    i += len("\\audio")

    n = len(src)

    # Skip whitespace
    while i < n and src[i].isspace():
        i += 1

    if i >= n or src[i] not in "[{":
        return None, start

    opts_raw: str | None = None
    url: str | None = None

    # Two supported syntaxes: {url}[opts] or [opts]{url}
    if src[i] == "{":
        # {url}[opts]
        try:
            url, i = _parse_braced_argument(src, i)
        except ValueError:
            return None, start

        # Skip whitespace before optional [...]
        j = i
        while j < n and src[j].isspace():
            j += 1
        if j < n and src[j] == "[":
            try:
                opts_raw, i = _parse_optional_bracket_argument(src, j)
            except ValueError:
                # Treat as if there were no options
                opts_raw = None
    else:
        # [opts]{url}
        try:
            opts_raw, i = _parse_optional_bracket_argument(src, i)
        except ValueError:
            return None, start

        while i < n and src[i].isspace():
            i += 1
        if i >= n or src[i] != "{":
            return None, start
        try:
            url, i = _parse_braced_argument(src, i)
        except ValueError:
            return None, start

    if url is None:
        return None, start

    key: str | None = None
    title: str | None = None
    pitch: str | None = None
    if opts_raw is not None:
        kv = _parse_keyval_options(opts_raw)
        key = kv.get("key") or None
        title = kv.get("title") or None
        pitch = kv.get("pitch") or None

    # Normalise simple TeX constructs in option values
    if key is not None:
        key = _tex_to_plain_text(key)
    if title is not None:
        title = _tex_to_plain_text(title)
    if pitch is not None:
        pitch = _tex_to_plain_text(pitch)

    normalised_url = _unescape_tex_url(url.strip())

    return AudioLink(url=normalised_url, key=key, title=title, pitch=pitch), i


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


def _find_midi_in_song_block(raw_song: str, doc_root: Path) -> Path | None:
    """
    Infer the MIDI file path for a song block, if any.

    Looks for a substring produced by lilypond-book containing lilypondbook and
    an \\input{...-systems.tex} call.

    Returns the MIDI file path relative to *doc_root*, or None if not found.
    """

    if "lilypondbook" not in raw_song:
        return None

    try:
        after = raw_song.split("lilypondbook", 1)[1]
        after_input = after.split("\\input{", 1)[1]
        input_arg = after_input.split("}", 1)[0].strip()
    except Exception:
        return None

    if not input_arg:
        return None

    # Derive MIDI filename from the "-systems.tex" helper filename
    midi_rel_str = input_arg.split("-systems.tex", 1)[0] + ".midi"
    return Path(midi_rel_str)


def _collapse_standalone_brace_groups(text: str) -> str:
    """Collapse non-macro '{...}' groups while keeping their contents.

    Braces that are not part of a macro call are removed, but their inner
    text is kept. Empty / whitespace-only groups are dropped entirely.
    """

    out: List[str] = []
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        if ch != "{":
            out.append(ch)
            i += 1
            continue
        try:
            inner, j = _parse_braced_argument(text, i)
        except ValueError:
            # Unbalanced brace; keep it verbatim and move on.
            out.append(ch)
            i += 1
            continue
        if inner.strip():
            out.append(inner)
        i = j
    return "".join(out)


def _skip_macro_arguments(src: str, start: int) -> int:
    """Skip typical macro arguments starting at *start*.

    This skips any immediate sequences of '(...)', '[...]' or '{...}'
    (including nested brackets/braces) and any surrounding whitespace.
    Returns the index of the first character after the skipped arguments.
    """

    i = start
    n = len(src)
    while i < n:
        # Skip whitespace between arguments
        while i < n and src[i].isspace():
            i += 1
        if i >= n:
            break

        ch = src[i]
        if ch == "[":
            try:
                _, i = _parse_optional_bracket_argument(src, i)
            except ValueError:
                # Give up on this bracket; treat it as ordinary text.
                break
            continue
        if ch == "(":
            depth = 1
            i += 1
            while i < n and depth > 0:
                if src[i] == "(":
                    depth += 1
                elif src[i] == ")":
                    depth -= 1
                i += 1
            continue
        if ch == "{":
            try:
                _, i = _parse_braced_argument(src, i)
            except ValueError:
                # Unbalanced; stop skipping to avoid an infinite loop.
                break
            continue
        break
    return i


def _strip_macros_for_lyrics(text: str) -> str:
    """Strip TeX macros and chord markup from a verse block for lyrics.

    Rules:
    - Remove the literal characters '|' and '^' everywhere.
    - Remove all TeX macros and their arguments, **except** macros listed in
      '_LYRICS_TEXT_MACROS_KEEP_ARG', for which the first braced argument's
      content is preserved.
    - Treat '\\[ ... ]' as a single chord macro whose entire body is
      discarded.
    - '\\\\' is converted to a newline character.
    - After macro removal, standalone '{...}' groups are collapsed by
      '_collapse_standalone_brace_groups()'.
    """

    # Remove barlines and caret markers used for repeated chords/notes.
    text = text.replace("|", "").replace("^", "")

    out: List[str] = []
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        if ch != "\\":
            out.append(ch)
            i += 1
            continue

        # Special case: chord macro \[ ... ]
        if text.startswith("\\[", i):
            i += 2
            depth_brace = 0
            while i < n:
                t = text[i]
                if t == "{":
                    depth_brace += 1
                elif t == "}":
                    if depth_brace > 0:
                        depth_brace -= 1
                elif t == "]" and depth_brace == 0:
                    i += 1
                    break
                i += 1
            continue

        # Special case: line break \\
        if text.startswith("\\\\", i):
            out.append("\n")
            i += 2
            continue

        # Control word (alphabetic macro name)
        j = i + 1
        if j < n and text[j].isalpha():
            while j < n and text[j].isalpha():
                j += 1
            macro_name = text[i + 1 : j]
            i = j
            # Optional star
            if i < n and text[i] == "*":
                i += 1

            if macro_name in _LYRICS_TEXT_MACROS_KEEP_ARG:
                # Preserve the first braced argument, stripping the macro
                # name and braces, and recursively cleaning its contents.
                while i < n and text[i].isspace():
                    i += 1
                if i < n and text[i] == "{":
                    try:
                        inner, j2 = _parse_braced_argument(text, i)
                    except ValueError:
                        i = _skip_macro_arguments(text, i)
                        continue
                    cleaned_inner = _strip_macros_for_lyrics(inner)
                    if cleaned_inner.strip():
                        out.append(cleaned_inner)
                    i = _skip_macro_arguments(text, j2)
                else:
                    # No braced argument; just skip macro name and any
                    # following arguments.
                    i = _skip_macro_arguments(text, i)
            elif macro_name == "jw":
                # Special case: \jw acts as a word separator. Emit a single
                # space regardless of how much whitespace follows it.
                out.append(" ")
                i = _skip_macro_arguments(text, i)
            else:
                # Uninteresting macro: remove it and its arguments entirely.
                i = _skip_macro_arguments(text, i)
            continue

        # Control symbol (non-alphabetic after backslash), e.g. \%.
        k = i + 1
        if k < n:
            esc = text[k]
            if esc == "%":
                out.append("%")
            else:
                out.append(esc)
            i = k + 1
        else:
            i = k

    # Second pass: collapse remaining standalone { ... } groups.
    return _collapse_standalone_brace_groups("".join(out))


def _normalise_verses(verses_raw: List[str]) -> Tuple[List[List[str]] | None, str | None]:
    """Normalise raw verse blocks into structured lines and a flat lowercase form.

    Shared by both lyrics and translation extraction.
    """

    if not verses_raw:
        return None, None

    verses: List[List[str]] = []
    for verse_src in verses_raw:
        # Drop TeX comments first.
        cleaned = re.sub(r"(?<!\\)%[^\r\n]*", "", verse_src)
        cleaned = _strip_macros_for_lyrics(cleaned)

        verse_lines: List[str] = []
        for raw_line in cleaned.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            # Collapse internal whitespace to a single space.
            line = re.sub(r"\s+", " ", line)
            if line:
                verse_lines.append(line)
        if verse_lines:
            verses.append(verse_lines)

    if not verses:
        return None, None

    verse_blocks = ["\n".join(v) for v in verses]
    joined = "\n\n".join(verse_blocks)
    return verses, joined.lower()


def _extract_lyrics_from_song_block(
    raw_song: str,
) -> Tuple[List[List[str]] | None, str | None]:
    """Extract structured lyrics from a '\\beginsong..\\endsong' block.

    Returns '(lyrics, lyrics_plain_lowercase)' where

    - 'lyrics' is a list of verses, each a list of cleaned lyric lines.
    - 'lyrics_plain_lowercase' is the same lyrics flattened into a single
      lowercase string, with '\n' between lines and '\n\n' between
      verses.

    On any parsing error, '(None, None)' is returned.
    """

    try:
        verses_raw: List[str] = []
        i = 0
        n = len(raw_song)
        while i < n:
            if raw_song.startswith("\\mnbeginverse", i):
                start = i + len("\\mnbeginverse")
                end = raw_song.find("\\mnendverse", start)
                if end == -1:
                    break
                verses_raw.append(raw_song[start:end])
                i = end + len("\\mnendverse")
                continue

            if raw_song.startswith("\\beginverse", i):
                start = i + len("\\beginverse")
                end = raw_song.find("\\endverse", start)
                if end == -1:
                    break
                verses_raw.append(raw_song[start:end])
                i = end + len("\\endverse")
                continue

            if raw_song.startswith("\\begin{verse}", i):
                start = i + len("\\begin{verse}")
                end = raw_song.find("\\end{verse}", start)
                if end == -1:
                    break
                verses_raw.append(raw_song[start:end])
                i = end + len("\\end{verse}")
                continue

            i += 1

        if not verses_raw:
            return None, None

        return _normalise_verses(verses_raw)

    except Exception:
        # Be conservative: if anything goes wrong, do not propagate errors
        # outside this module.
        return None, None


def _extract_translations_from_song_block(raw_song: str) -> List[Translation]:
    """Extract all translation blocks from a '\\beginsong..\\endsong' block.

    Each translation block is either::

        \\begin{translation}[LC] ... \\end{translation}
        \\begintranslation[LC] ... \\endtranslation

    where 'LC' is an optional language code. Verses inside a translation
    block are separated with '\\nextverse'.

    Returns a list of Translation instances. On any parsing error, an
    empty list is returned.
    """

    translations: List[Translation] = []
    try:
        i = 0
        n = len(raw_song)
        while i < n:
            if raw_song.startswith("\\begin{translation}", i):
                start = i + len("\\begin{translation}")
                j = start
                while j < n and raw_song[j].isspace():
                    j += 1
                lang: str | None = None
                if j < n and raw_song[j] == "[":
                    lang_raw, j = _parse_optional_bracket_argument(raw_song, j)
                    if lang_raw is not None:
                        lang_raw = lang_raw.strip()
                        if lang_raw:
                            lang = lang_raw.lower()
                content_start = j
                end_token = "\\end{translation}"
                end = raw_song.find(end_token, content_start)
                if end == -1:
                    break
                body = raw_song[content_start:end]
                i = end + len(end_token)
            elif raw_song.startswith("\\begintranslation", i):
                start = i + len("\\begintranslation")
                j = start
                while j < n and raw_song[j].isspace():
                    j += 1
                lang: str | None = None
                if j < n and raw_song[j] == "[":
                    lang_raw, j = _parse_optional_bracket_argument(raw_song, j)
                    if lang_raw is not None:
                        lang_raw = lang_raw.strip()
                        if lang_raw:
                            lang = lang_raw.lower()
                content_start = j
                end_token = "\\endtranslation"
                end = raw_song.find(end_token, content_start)
                if end == -1:
                    break
                body = raw_song[content_start:end]
                i = end + len(end_token)
            else:
                i += 1
                continue

            # Drop TeX comments so that commented-out \\nextverse markers do
            # not split verses.
            body = re.sub(r"(?<!\\)%[^\r\n]*", "", body)
            verses_raw = body.split("\\nextverse")

            verses, plain_lower = _normalise_verses(verses_raw)
            if verses is None or plain_lower is None:
                continue
            translations.append(
                Translation(language=lang, lyrics=verses, lyrics_plain_lowercase=plain_lower)
            )
        return translations
    except Exception:
        return []


# Main walker
# ===========


def _relative_to_doc_root(path: Path, doc_root: Path) -> Path:
    """Return *path* relative to *doc_root* when possible.

    Falls back to the absolute path when *path* is not inside *doc_root*.
    """

    try:
        return path.resolve().relative_to(doc_root.resolve())
    except Exception:
        return path


def _apply_book_field(book_info: BookInfo, field_name: str, value: str) -> None:
    """
    Set field_name on book_info, normalising simple TeX constructs.
    """

    cleaned = _tex_to_plain_text(value)
    object.__setattr__(book_info, field_name, cleaned)


def build_song_database(
    processed_tex: Path, include_search_paths: Sequence[Path], variant: str = "unknown"
) -> SongbookData:
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
    book_info.variant = variant
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

        raw_title = title.strip()
        # Split possible alternative titles on explicit TeX line breaks.
        parts = [p.strip() for p in re.split(r"\\\\", raw_title) if p.strip()]
        if parts:
            main_title = _tex_to_plain_text(parts[0])
            alt_titles = [_tex_to_plain_text(p) for p in parts[1:]]
        else:
            main_title = ""
            alt_titles = []

        title_slug = _slugify(main_title, default="song")
        number = current_songnum
        if current_songnum is None:
            number = None
        else:
            current_songnum += 1

        # Normalise simple TeX constructs in \beginsong options as well.
        normalised_options: Dict[str, str] = {k: _tex_to_plain_text(v) for k, v in options.items()}

        midi_compile_file_relative = _find_midi_in_song_block(raw_block, doc_root)
        audio_links = _collect_audio_links_from_block(raw_block)
        lyrics, lyrics_plain_lowercase = _extract_lyrics_from_song_block(raw_block)
        translations = _extract_translations_from_song_block(raw_block)

        source_file_relative = _relative_to_doc_root(tex_file, doc_root)

        order_counter += 1
        song = SongInfo(
            title=main_title,
            title_slug=title_slug,
            number=number,
            options=normalised_options,
            source_file_relative=source_file_relative,
            midi_compile_file_relative=midi_compile_file_relative,
            order_index=order_counter,
            chapter_title=current_chapter.title if current_chapter else None,
            chapter_slug=current_chapter.slug if current_chapter else None,
            alt_titles=alt_titles,
            audio_links=audio_links,
            lyrics=lyrics,
            lyrics_plain_lowercase=lyrics_plain_lowercase,
            translations=translations,
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

            # \documentclass
            # \\PassOptionsToClass{options}{class}
            if src.startswith("\\PassOptionsToClass", i):
                i += len("\\PassOptionsToClass")
                while i < n and src[i].isspace():
                    i += 1
                if i >= n or src[i] != "{":
                    continue
                try:
                    opts_raw, i = _parse_braced_argument(src, i)
                except ValueError:
                    continue
                # Skip whitespace before class-name argument and parse it to
                # advance the cursor, but we don't currently use it.
                while i < n and src[i].isspace():
                    i += 1
                if i < n and src[i] == "{":
                    try:
                        _, i = _parse_braced_argument(src, i)
                    except ValueError:
                        pass
                if opts_raw:
                    for opt_key, opt_val in _parse_keyval_options(opts_raw).items():
                        field_name = _BOOK_OPTION_TO_FIELD.get(opt_key)
                        if field_name is not None:
                            _apply_book_field(book_info, field_name, opt_val)
                continue

            # \\documentclass
            if src.startswith("\\documentclass", i):
                i += len("\\documentclass")
                while i < n and src[i].isspace():
                    i += 1
                # Optional [key=val,...] options
                opts_raw, i = _parse_optional_bracket_argument(src, i)
                while i < n and src[i].isspace():
                    i += 1
                # Required {classname}
                classname: str | None = None
                if i < n and src[i] == "{":
                    try:
                        classname, i = _parse_braced_argument(src, i)
                    except ValueError:
                        classname = None
                if classname:
                    classname = classname.strip()
                    # The first encountered document class is the most specific
                    # one; keep it.
                    if book_info.document_class is None:
                        book_info.document_class = classname
                    # Also process the corresponding .cls file recursively so
                    # that any \renewcommand definitions it contains are seen.
                    cls_path = _resolve_documentclass(classname, path, search_paths)
                    if cls_path is not None:
                        process_file(cls_path)
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
                if src.startswith("\\ulMainChapter", i):
                    macro = "\\ulMainChapter"
                elif src.startswith("\\songchapter", i):
                    macro = "\\songchapter"
                else:
                    macro = "\\chapter"
                i += len(macro)

                # For ulMainChapter, the syntax is
                #   \ulMainChapter[short]{long}{colorname}
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
                    raw_title, i = _parse_braced_argument(src, i)
                except ValueError:
                    continue

                display_title = _tex_to_plain_text(raw_title.strip())
                slug = _slugify(display_title, default="chapter")
                source_file_relative = _relative_to_doc_root(path, doc_root)
                chap = ChapterInfo(
                    title=display_title,
                    slug=slug,
                    source_file_relative=source_file_relative,
                )
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

    db_source_file_relative = _relative_to_doc_root(processed_tex, doc_root)
    creation_time = datetime.now(timezone.utc).isoformat()

    return SongbookData(
        book_info=book_info,
        chapters=chapters,
        songs_without_chapter=songs_without_chapter,
        source_file_relative=db_source_file_relative,
        total_songs=order_counter,
        creation_time=creation_time,
    )
