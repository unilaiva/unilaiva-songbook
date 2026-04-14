# Unilaiva Songbook

This repository contains the **Unilaiva Songbook** sources and the
project-specific files needed to build the published books with
[ULSBS](https://github.com/unilaiva/ulsbs/blob/main/README.md) (Unilaiva Songbook System).

> [!IMPORTANT]
> Published PDFs built from this repository are available at:
> - [Unilaiva Songbook](https://unilaiva.aavalla.net/)
> - [Astral books](https://unilaiva-astral.aavalla.net/)

---

- [Unilaiva Songbook](#unilaiva-songbook)
  - [Repository change notice (2026-04-13)](#repository-change-notice-2026-04-13)
  - [Quick start](#quick-start)
    - [Platform-specific setup](#platform-specific-setup)
      - [Ubuntu or Debian](#ubuntu-or-debian)
      - [macOS](#macos)
      - [Windows](#windows)
  - [Repository layout](#repository-layout)
  - [Editing this repository](#editing-this-repository)
  - [Output](#output)
  - [Printing](#printing)
    - [Printing double sided on a single sided printer](#printing-double-sided-on-a-single-sided-printer)
      - [Example procedure for printing on a single sided printer](#example-procedure-for-printing-on-a-single-sided-printer)
  - [Updating](#updating)
  - [ULSBS documentation](#ulsbs-documentation)
  - [Status](#status)
  - [Copyright and Licensing](#copyright-and-licensing)

---

## Repository change notice (2026-04-13)

> [!IMPORTANT]
> On 2026-04-13 this repository changed in two important ways:
> - the primary branch is now `main` instead of `master`
> - ULSBS was split into its own repository and is now included here as the `ulsbs/` git submodule
>
> Split-related commits in this repository:
> - `0cfc3bd` — Remove embedded ulsbs after repository split
> - `a626fcd` — Add ulsbs as submodule
> - `33acbfb` — Use HTTPS URL for ulsbs submodule
> - `9dfec62` — Add update-repository script to update repo and submodules

If you cloned this repository before these changes, first make sure you do not
have uncommitted work. Old clones may still be configured to fetch only the
removed `master` branch, so fetch `main` explicitly and update the local branch
tracking like this:

```sh
git remote set-branches origin '*'
git fetch origin main:refs/remotes/origin/main
git branch -m master main 2>/dev/null || true
git branch --set-upstream-to=origin/main main
git remote set-head origin -a
git pull --rebase
git submodule sync --recursive
git submodule update --init --recursive
```

If Git refuses to create the submodule because `ulsbs/` already exists as a
normal directory in your old clone, move that directory away or remove it
first, then run the last two submodule commands again. After the migration,
normal updates can be done with:

```sh
./update-repository
```

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

### Platform-specific setup

The recommended way to build this repository is the default container mode.
That means you mainly need:

- `git`
- `python3` 3.11+
- Docker or Podman

#### Ubuntu or Debian

Install the basic tools and Docker, then clone and build:

```sh
sudo apt update
sudo apt install docker.io git python3
sudo usermod -aG docker "$USER"
newgrp docker
git clone --depth 1 --recurse-submodules https://github.com/unilaiva/unilaiva-songbook.git
cd unilaiva-songbook
./ulsbs-compile
```

If you prefer Podman, install `podman` instead of `docker.io`.

#### macOS

1. Install Docker Desktop: <https://docs.docker.com/desktop/setup/install/mac-install/>
2. Install Python 3.11+ from <https://www.python.org/downloads/macos/>
3. If `git` is missing, install Xcode Command Line Tools with:

```sh
xcode-select --install
```

Start Docker Desktop once, then clone and build:

```sh
git clone --depth 1 --recurse-submodules https://github.com/unilaiva/unilaiva-songbook.git
cd unilaiva-songbook
./ulsbs-compile
```

#### Windows

Use WSL2 with Ubuntu. Keeping the repository inside the Linux home directory is
recommended for symlink support and better performance.

1. In PowerShell, install WSL2:

```sh
wsl --install -d Ubuntu
```

2. Install Docker Desktop for Windows and enable WSL integration for the Ubuntu
   distro: <https://docs.docker.com/desktop/setup/install/windows-install/>
3. Open the Ubuntu shell and run:

```sh
sudo apt update
sudo apt install git python3
cd ~
git clone --depth 1 --recurse-submodules https://github.com/unilaiva/unilaiva-songbook.git
cd unilaiva-songbook
./ulsbs-compile
```

Optional: to copy final outputs directly to your Windows home directory, use
for example:

```sh
./ulsbs-compile --deploy-dir "/mnt/c/Users/<USERNAME>/unilaiva-result"
```

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
ULSBS usage outside this repository, see [ulsbs/README.md](https://github.com/unilaiva/ulsbs/blob/main/README.md).

To later update the repository, run in the project's root:

`./update-repository`

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
[ulsbs/README.md](https://github.com/unilaiva/ulsbs/blob/main/README.md).

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
[`ulsbs-tex-tools`](https://github.com/unilaiva/ulsbs/blob/main/vscode-extension/ulsbs-tex-tools/README.md)
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

The main books are intended primarily for **A5** printing (148 mm × 210 mm).

In the simplest case, print the main document, `unilaiva-songbook_A5.pdf`, on
A5 paper, and make sure A5 is selected in the printing software. Otherwise the
pages may be scaled up or printed with overly wide margins.

For double-sided printing, make sure the pages are oriented so that odd pages
appear on the right-hand side (recto) and even pages on the left-hand side
(verso) of each spread. This minimizes page-turning within a song, because all
songs that span at least two pages begin on an even page. The margins, page
number positions, and similar layout details are also optimized for this order.

If possible, set margins to zero both in the printing software and in the
printer driver settings. On Linux and macOS, the `lp` program is recommended
for printing without extra margins. For example:
`lp -o PageSize=A4 printout-BOOKLET_unilaiva-songbook_A5-on-A4-doublesided-needs-cutting.pdf`
Do not use a `fit-to-page` option, which some GUI printing programs may enable
by default.

The build also generates additional printout PDFs for printing A5 pages on A4
sheets. These are often the easiest files to use for home printing.

For the main songbook (the default variant), the most relevant outputs are
usually:

- `result/unilaiva-songbook_A5.pdf`
- `result/printouts/printout-EASY_unilaiva-songbook_A5-on-A4-sidebyside-simple.pdf`
- `result/printouts/printout-BOOKLET_unilaiva-songbook_A5-on-A4-doublesided-needs-cutting.pdf`

### Printing double sided on a single sided printer

To print double-sided on a printer without a duplexer, first print the odd
pages, then flip and re-feed the paper, and finally print the even pages. For
the main document, `unilaiva-songbook_A5.pdf`, the pages must be flipped on the
long edge. For the other files named `printout-*unilaiva-songbook*.pdf`, which
place multiple pages on each A4 sheet, the pages should be flipped on the short
edge.

To flip pages *on the short edge* manually, place the printed stack in front of
you upside down, with the printed side hidden. Then create a new stack by
moving each sheet one by one from the top of the old stack to the top of the
new stack, without rotating or turning the sheets in any way. Feed the new
stack into the printer, taking care to insert it in the correct orientation.

If your printing software is limited, you can for example use `pdftk` to
extract odd and even pages:

- `pdftk unilaiva-songbook_A5.pdf cat 1-endodd output unilaiva-songbook_odd.pdf`
- `pdftk unilaiva-songbook_A5.pdf cat 1-endeven output unilaiva-songbook_even.pdf`

#### Example procedure for printing on a single sided printer

This procedure prints the entire book on A4 paper with a printer that supports
single-sided printing only. Flipping pages, cutting, and binding are all done
by hand. The final result is a book of double-sided A5 pages, which is the
preferred format.

1. `./ulsbs-compile`
2. `pdftk result/printouts/printout-BOOKLET_unilaiva-songbook_A5-on-A4-doublesided-needs-cutting.pdf cat 1-endodd output unilaiva-songbook_odd.pdf`
3. `pdftk result/printouts/printout-BOOKLET_unilaiva-songbook_A5-on-A4-doublesided-needs-cutting.pdf cat 1-endeven output unilaiva-songbook_even.pdf`
4. `lp -o PageSize=A4 unilaiva-songbook_odd.pdf`
5. Flip the pages manually on the short edge and feed them back into the printer.
6. `lp -o PageSize=A4 unilaiva-songbook_even.pdf`
7. Cut the A4 pages in half to make A5 pages, and arrange them in the correct order.
8. Punch holes and bind the book.

## Updating

If your clone predates the 2026-04-13 branch/submodule migration, follow the
steps in [Repository change notice (2026-04-13)](#repository-change-notice-2026-04-13) once first.

To update both this repository and the ULSBS submodule:

```sh
./update-repository
```

## ULSBS documentation

Most technical documentation now lives in the submodule README:

- [ulsbs/README.md](https://github.com/unilaiva/ulsbs/blob/main/README.md)

That README covers:

- how ULSBS works
- how to use ULSBS in another songbook repository or local directory
- compilation options and configuration
- songbook syntax
- Lilypond integration
- helper tools such as `ulsbs-ly2tex` and `ulsbs-bookmeta`
- editor support

## Status

ULSBS is still under active development. This repository is kept in sync with
current ULSBS behavior, but external songbook projects using ULSBS should be
prepared to adjust their sources when upgrading until a stable 1.0 release is
made.

## Copyright and Licensing

Unless otherwise noted, the editorial material in these songbooks —
including musical transcriptions, chord charts, arrangements, engraving,
and typesetting — is licensed under the Creative Commons Attribution-
NonCommercial-ShareAlike 4.0 International License (CC BY-NC-SA 4.0).

Many songs included in this collection are traditional folk songs and are
believed to be in the public domain. When known, the source or author of
each song is indicated.

Some songs may still be protected by copyright. Such material is included
either with permission or in good faith for educational and community use.

The Creative Commons license applies only to the editorial contributions
made in this edition and does not affect the copyright status of the
underlying songs where such rights exist.

Every effort has been made to identify and credit rights holders where
possible. If you believe that any material in this book infringes copyright,
please contact the editors so that the matter can be reviewed and the
material corrected or removed if necessary.

These songbooks were produced using the Unilaiva Songbook System (ULSBS),
which is free software licensed under the GNU General Public License
version 3 or later (GPL 3.0+).
