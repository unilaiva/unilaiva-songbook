# Unilaiva Songbook

This repository contains the **Unilaiva Songbook** sources and the
project-specific files needed to build the published books with
[ULSBS](./ulsbs/README.md) (Unilaiva Songbook System).

> [!IMPORTANT]
> Published PDFs built from this repository are available at:
> - [Unilaiva Songbook](https://unilaiva.aavalla.net/)
> - [Astral books](https://unilaiva-astral.aavalla.net/)

## Quick start

Clone the repository together with the ULSBS submodule:

```sh
git clone --depth 1 --recurse-submodules https://github.com/unilaiva/unilaiva-songbook.git
cd unilaiva-songbook
./ulsbs-compile
```

If you already cloned without submodules, run:

```sh
git submodule update --init --recursive
```

The default build compiles all configured books in this repository.

Useful commands:

- Build everything configured in `ulsbs-config.toml`:
  - `./ulsbs-compile`
- Build only the main Unilaiva books:
  - `./ulsbs-compile --profile main`
- Build only Astral books:
  - `./ulsbs-compile --profile astral`
- Build one document only:
  - `./ulsbs-compile unilaiva-songbook_A5.tex`
- Fast local dev build:
  - `./ulsbs-compile --quick unilaiva-songbook_A5.tex`

For containerless builds, full toolchain requirements, CLI options, and generic
ULSBS usage outside this repository, see [ulsbs/README.md](./ulsbs/README.md).

## Repository layout

Top-level files and directories you are most likely to need:

- `unilaiva-songbook_A5.tex`
  - main full Unilaiva book
- `unilaiva-songbook_part1_A5.tex`, `unilaiva-songbook_part2_A5.tex`
  - split versions of the main book
- `unilaiva-astral-*.tex`
  - Astral books
- `ul-selection_new-songs_A5.tex`
  - an example/custom selection book in active use
- `content/`
  - songs, explanations, and other included content
- `include/`
  - shared includes, class files, and selection helpers
- `assets/`
  - deployment metadata and other project assets
- `ulsbs-config.toml`
  - repository-specific build configuration and profiles
- `ulsbs/`
  - the ULSBS engine as a git submodule
- `workspace/`
  - scratch material and helper files for editing/transcribing

## Editing this repository

For the actual songbook syntax and ULSBS-specific markup, see
[ulsbs/README.md](./ulsbs/README.md).

Repository-specific pointers:

- Most song texts live in `content/songs_*.tex`.
- Non-song prose sections also live in `content/`.
- Main books in the project root select and arrange content chapters.
- Project-specific class defaults live in:
  - `include/ulsbs-songbook-unilaiva-default.cls`
  - `include/ulsbs-songbook-astral-default.cls`
- Available tags are listed in `include/tags.can`.
- Example selection setup is in `include/ul-selection_example.tex`.

If you use VS Code, the bundled extension
[`ulsbs-tex-tools`](./ulsbs/vscode-extension/ulsbs-tex-tools/README.md)
provides helpful editing support for ULSBS LaTeX files.

## Output

Compiled files are written under `result/`. Depending on configuration and
available tools, the build may also produce:

- lyrics-only variants
- extra instrument variants
- JSON exports
- MIDI files
- MP3 audio
- cover PNGs
- printout PDFs for home printing

If deployment is enabled, files are also copied under `deploy/`.

## Printing

The main books are designed primarily for **A5** printing.

If ConTeXt is installed, the build also generates extra printout PDFs for
printing A5 pages on A4 sheets. Those are usually the easiest files to use for
home printing.

For the main full book, the most relevant outputs are typically:

- `result/unilaiva-songbook_A5.pdf`
- `result/printout-BOOKLET_unilaiva-songbook_A5-on-A4-doublesided-needs-cutting.pdf`

When printing duplex, make sure odd pages end up on the right-hand side of each
spread.

## Updating

To update both this repository and the ULSBS submodule:

```sh
./update-repository
```

## ULSBS documentation

Most technical documentation now lives in the submodule README:

- [ulsbs/README.md](./ulsbs/README.md)

That README covers:

- how ULSBS works
- how to use ULSBS in another songbook repository or local directory
- compilation options and configuration
- songbook syntax
- Lilypond integration
- helper tools such as `ulsbs-ly2tex` and `ulsbs-book2json`
- editor support

## Status

ULSBS is still under active development. This repository is kept in sync with
current ULSBS behavior, but external songbook projects using ULSBS should be
prepared to adjust their sources when upgrading until a stable 1.0 release is
made.
