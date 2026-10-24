# Unilaiva Songbook

This repository contains the **Unilaiva Songbook** and **Astral books**: song
texts, chords, musical transcriptions, and the project-specific files used to
build their PDFs. The reusable compiler and typesetting engine is
[ULSBS](https://github.com/unilaiva/ulsbs), included here as the `ulsbs/` Git submodule.

**Read or download the published books:**

- [Unilaiva Songbook](https://unilaiva.aavalla.net/)
- [Astral books](https://unilaiva-astral.aavalla.net/)

You do not need to install anything to download the published PDFs. To edit
these collections or compile your own local copies, follow the quick start
below. To create an independent songbook project, start with the
[ULSBS setup guide](https://github.com/unilaiva/ulsbs/blob/main/README.md) instead.

## Contents

- [Contents](#contents)
- [Quick start](#quick-start)
- [Compiling books](#compiling-books)
- [Platform-specific setup](#platform-specific-setup)
  - [Ubuntu or Debian](#ubuntu-or-debian)
  - [macOS](#macos)
  - [Windows](#windows)
- [Repository layout](#repository-layout)
- [Editing this repository](#editing-this-repository)
- [Output](#output)
- [Printing](#printing)
  - [Print settings](#print-settings)
  - [Printing double sided on a single sided printer](#printing-double-sided-on-a-single-sided-printer)
- [Updating](#updating)
  - [Repository change notice (2026-04-13)](#repository-change-notice-2026-04-13)
- [ULSBS documentation](#ulsbs-documentation)
- [Status](#status)
- [Contact](#contact)
- [Copyright and Licensing](#copyright-and-licensing)

## Quick start

The recommended build uses Docker or Podman, which supplies LaTeX, LilyPond,
fonts, and the other compiler dependencies. On your computer you need Git,
`bash`, Python 3.11+, and a working Docker or Podman installation. See
[platform-specific setup](#platform-specific-setup) if these are not installed.
Start Docker Desktop before compiling if you use it.

Clone the repository **with its submodule**, then build just the main Unilaiva PDF:

```sh
git clone --depth 1 --recurse-submodules https://github.com/unilaiva/unilaiva-songbook.git
cd unilaiva-songbook
./ulsbs-compile --quick unilaiva-songbook_A5.tex
```

Open `result/unilaiva-songbook_A5.pdf`. The first run also builds the compiler
image and takes longer than later runs. `--quick` omits additional variants,
multikey editions, printouts, covers, and media exports, skips deployment, and
keeps intermediate files for troubleshooting.
It still typesets the main book, including its original LilyPond notation.

If you already cloned without submodules, run this from the project root first:

```sh
git submodule update --init --recursive
```

For a clone from before the April 2026 repository split, see the
[migration instructions](#repository-change-notice-2026-04-13).

## Compiling books

Run build commands from the repository root. This repository enables multikey
editions, including score transposition, in its configuration. Normal builds
can therefore take substantially longer than a quick main-PDF check.

| Task | Command |
|---|---|
| Fast check of the main Unilaiva PDF | `./ulsbs-compile --quick unilaiva-songbook_A5.tex` |
| Build one book with its enabled extras | `./ulsbs-compile unilaiva-songbook_A5.tex` |
| Build the full and split Unilaiva books | `./ulsbs-compile --profile main` |
| Build the Astral books | `./ulsbs-compile --profile astral` |
| Build all configured root documents | `./ulsbs-compile` |
| Build one book without multikey companions | `./ulsbs-compile --no-multikey unilaiva-songbook_A5.tex` |
| Verbose, non-deploying build of one book | `./ulsbs-compile --profile dev unilaiva-songbook_A5.tex` |
| Reduce concurrent memory use | Add `--sequential` to a build command |

The actual book selections and shared output settings are in
[`ulsbs-config.toml`](ulsbs-config.toml). The `default` profile selects all
root-level TeX documents, including selection books; `main` and `astral` filter
that selection by filename. Explicit `.tex` arguments override profile book
selection.

This repository's `dev` profile only disables deployment and enables verbose
output. It does not define a book list or turn off extra variants or multikey
editions, so supply a document explicitly and add `--quick` when you want a fast check.
Its settings are independent of the illustrative profiles in ULSBS's example
configuration.

Other useful flags are `--no-deploy`, `--keep-temp`, and `--max-log-lines 100`.
Run `./ulsbs-compile --help` for all options. For containerless builds and the
full toolchain requirements, see the
[ULSBS requirements](https://github.com/unilaiva/ulsbs/blob/main/README.md#requirements).

## Platform-specific setup

These steps install prerequisites. Afterwards, follow the
[quick start](#quick-start) to clone and compile the repository.

### Ubuntu or Debian

On Ubuntu 24.04 or Debian 12 and newer, install the basic tools and Docker:

```sh
sudo apt update
sudo apt install docker.io git python3
sudo usermod -aG docker "$USER"
newgrp docker
```

If you prefer Podman, install `podman` instead of `docker.io` and omit the
Docker group commands. Use `--container-engine podman` to select it explicitly
when both engines are installed. On older distributions, check that `python3`
is version 3.11 or newer.

### macOS

1. Install [Docker Desktop](https://docs.docker.com/desktop/setup/install/mac-install/).
2. Install [Python 3.11+](https://www.python.org/downloads/macos/).
3. If Git is missing, run `xcode-select --install` to install Xcode Command Line Tools.
4. Start Docker Desktop before compiling.

### Windows

Use WSL2 with Ubuntu, keeping the repository inside the Linux home directory
for symlink support and better filesystem performance.

1. In PowerShell, run `wsl --install -d Ubuntu`.
2. Install Docker Desktop and enable
   [WSL integration for Ubuntu](https://docs.docker.com/desktop/setup/install/windows-install/).
3. In the Ubuntu shell, run `sudo apt update` and `sudo apt install git python3`.
4. Run `cd ~`, then follow the quick start from that Ubuntu shell.

To copy normal-build outputs to your Windows home directory, replace
`<USERNAME>` with your Windows username and use an existing destination:

```sh
mkdir -p "/mnt/c/Users/<USERNAME>/unilaiva-result"
./ulsbs-compile --deploy-dir "/mnt/c/Users/<USERNAME>/unilaiva-result" unilaiva-songbook_A5.tex
```

An explicitly selected deployment directory must already exist. Deployment is
disabled by `--quick`, so use a normal build for this copy.

## Repository layout

| Path | Purpose |
|---|---|
| [`unilaiva-songbook_A5.tex`](unilaiva-songbook_A5.tex) | Full Unilaiva book |
| `unilaiva-songbook_part1_A5.tex`, `unilaiva-songbook_part2_A5.tex` | Split Unilaiva books |
| `unilaiva-astral-*.tex` | Astral books |
| [`ul-selection_new-songs_A5.tex`](ul-selection_new-songs_A5.tex) | An existing custom selection book |
| `content/` | Songs, prose, and images included in books |
| `include/` | Project-specific classes, shared includes, tags, and selection helpers |
| `assets/` | Website catalog metadata, deployment assets, and media-directory READMEs |
| [`ulsbs-config.toml`](ulsbs-config.toml) | This repository's build settings and profiles |
| `ulsbs/` | Reusable ULSBS engine, pinned as a Git submodule |
| `workspace/` | Scratch material and transcription/editing helpers |
| `ulsbs-compile`, `update-repository` | Build and update wrappers |

The website catalog format is documented in [`assets/README.md`](assets/README.md).
It is separate from the compiler's generated per-book JSON exports.

## Editing this repository

For song syntax, start with
[Writing Songbooks](https://github.com/unilaiva/ulsbs/blob/main/WRITING_SONGBOOKS.md).
Repository-specific conventions are:

- Most songs live in `content/songs_*.tex`; non-song prose also lives in `content/`.
- Main documents in the root select and arrange the content chapters.
- The Unilaiva and Astral style defaults are in
  [`include/ulsbs-songbook-unilaiva-default.cls`](include/ulsbs-songbook-unilaiva-default.cls)
  and [`include/ulsbs-songbook-astral-default.cls`](include/ulsbs-songbook-astral-default.cls).
- Song tags are defined in [`include/tags.can`](include/tags.can).
- [`include/ul-selection_example.tex`](include/ul-selection_example.tex) shows
  the project's selection setup; read its associated helper defaults before copying it.

A practical edit/check cycle is:

1. Find the main document that includes the song collection you want to edit.
2. Edit the source, preserving stable song IDs and checking attribution and key metadata.
3. Compile that main document with `--quick` and inspect the generated PDF.
4. Before publishing, build the required variants and editions and inspect their layout too.

The bundled
[ULSBS TeX Tools extension](https://github.com/unilaiva/ulsbs/blob/main/vscode-extension/ulsbs-tex-tools/README.md)
adds VS Code snippets, song navigation, diagnostics, and build commands. Open
this repository's root as the workspace so it can find the config and engine.
Other text editors also work.

## Output

Normal builds can produce these files, depending on settings, tools, and source
content:

| Location | Content |
|---|---|
| `result/` | Ordinary PDFs of the default and enabled lyrics-only/instrument variants |
| `result/printouts/` | A5-on-A4 home-printing PDFs |
| `result/multikey/` | Multikey indices and layered page-range PDFs |
| `result/json/` | Generated per-book metadata/search exports |
| `result/midi/`, `result/audio/` | MIDI and MP3 files from supported LilyPond scores |
| `result/images/` | Cover images |
| `deploy/` | Copies of published outputs plus configured website/deployment assets |

Quick builds omit additional variants, multikey editions, and most extra outputs.
Deployment is a local copy, not a website upload; `--no-deploy` disables it for a normal build.
Songs containing only LaTeX lyrics and chords do not generate MIDI or audio.

Default, lyrics-only, and instrument outputs are variants of the same source.
The compiler currently generates multikey editions for default and instrument
variants, not lyrics-only variants.

Multikey editions consist of an index and its range PDFs, not one full-book PDF.
Keep them together with the matching ordinary PDF when publishing updates.
Live websites need a consistent ordinary-PDF/index/ranges snapshot; see
[multikey guidance](https://github.com/unilaiva/ulsbs/blob/main/README.md#multikey-pdf-editions)
for viewer compatibility and deployment details. Use ordinary PDFs for conventional printing.

## Printing

The main books are designed for **A5** (148 mm x 210 mm). Use the ordinary PDF
for printing, not a layered multikey range. Choose the output that matches your
paper and binding method:

| Output | Paper | Intended use |
|---|---|---|
| `result/unilaiva-songbook_A5.pdf` | A5 | Print the book directly at its original size |
| `result/printouts/printout-EASY_unilaiva-songbook_A5-on-A4-sidebyside-simple.pdf` | A4 | Read facing A5 pages side by side on intact A4 sheets |
| `result/printouts/printout-BOOKLET_unilaiva-songbook_A5-on-A4-doublesided-needs-cutting.pdf` | A4 | Double-sided output for making an A5 book; cut and arrange pages for binding |

The `EASY` layout preserves facing spreads and inserts an initial blank page.
When printed double-sided, it is **not** intended for cutting or folding into
an A5 book. The `BOOKLET` layout uses a different page arrangement for that purpose.

Printouts are generated by normal builds, not `--quick` builds. For example:

```sh
./ulsbs-compile --no-multikey --no-deploy unilaiva-songbook_A5.tex
```

This keeps printout generation enabled while omitting multikey companions and
deployment; other normal extras remain enabled. You can also download published
printout PDFs rather than compiling them yourself.

### Print settings

- Select the actual paper size: A5 for the ordinary PDF, A4 for the printouts.
- Use actual size / 100% scale, not fit-to-page or additional booklet imposition.
- Set extra software/driver margins to zero where the printer supports it.
- Keep the original page order, including the cover and preliminary pages.
- For double-sided A5 output, use long-edge flipping. For these landscape A4
  printouts, use short-edge flipping. Test a few pages before printing the full book.

The facing-page layout puts odd pages on the right (recto) and even pages on the
left (verso), with margins and headers designed accordingly.

On Linux and macOS, `lp` can submit a PDF without a GUI's extra scaling options:

```sh
lp -o PageSize=A4 result/printouts/printout-BOOKLET_unilaiva-songbook_A5-on-A4-doublesided-needs-cutting.pdf
```

Check the printer's duplex, orientation, and scaling defaults before submitting
a full book. Printer-specific settings and the physical sheet-feed direction vary.

### Printing double sided on a single sided printer

For manual duplex printing, print the odd PDF pages first, reinsert the sheets,
then print the even PDF pages. Reinsert for the correct flipping edge above;
some printers also need the stack order reversed. Test with a few sheets to
establish the correct feed orientation rather than assuming a universal procedure.

If your printing software cannot select odd/even pages, the optional host tool
`pdftk` can split them. From the repository root:

```sh
book="result/printouts/printout-BOOKLET_unilaiva-songbook_A5-on-A4-doublesided-needs-cutting.pdf"
pdftk "$book" cat 1-endodd output unilaiva-songbook_odd.pdf
pdftk "$book" cat 1-endeven output unilaiva-songbook_even.pdf
```

These select physical PDF pages, not printed page labels. To print the two passes:

1. Print `unilaiva-songbook_odd.pdf` on A4, single-sided.
2. Reinsert the stack for short-edge flipping, using the orientation/order established by your test.
3. Print `unilaiva-songbook_even.pdf` on the reverse sides, also single-sided.
4. Cut the A4 sheets into A5 pages, arrange them in order, and bind the book.

For example, the first pass can be submitted with:

```sh
lp -o PageSize=A4 -o sides=one-sided unilaiva-songbook_odd.pdf
```

After reinserting the stack, use the same command with
`unilaiva-songbook_even.pdf`. `lp` and `pdftk` are printing-side tools, not
requirements for the normal container build.

## Updating

Save your local work in both this repository and the `ulsbs/` submodule before
updating. From the repository root, run:

```sh
./update-repository
```

The wrapper runs `git pull --rebase`, then initializes/updates submodules to
the revisions recorded by the parent repository. It does not independently
advance ULSBS to its latest upstream commit. If Git reports local changes or
conflicts, resolve those before retrying; do not delete local work to update.

### Repository change notice (2026-04-13)

On 2026-04-13 the primary branch changed from `master` to `main`, and ULSBS
moved into its own repository, included here as the `ulsbs/` submodule. Fresh
clones already use this layout. The following recovery steps are only for
older clones; make sure your local work is saved first.

An old clone may still fetch only the removed `master` branch. Fetch `main` explicitly:

```sh
git remote set-branches origin '*'
git fetch origin main:refs/remotes/origin/main
```

If your local main branch is still called `master` and no local `main` exists,
switch to it and rename it:

```sh
git switch master
git branch -m main
```

If local `main` already exists, use `git switch main` instead. Then finish
updating its tracking configuration and submodules:

```sh
git branch --set-upstream-to=origin/main main
git remote set-head origin -a
git pull --rebase
git submodule sync --recursive
git submodule update --init --recursive
```

If Git refuses to create the submodule because `ulsbs/` still exists as an old
ordinary directory, move that directory aside after preserving any local edits,
then retry the submodule commands. Normal later updates use `./update-repository`.

For historical reference, the split-related commits are `0cfc3bd` (remove the
embedded engine), `a626fcd` (add the submodule), `33acbfb` (use its HTTPS URL),
and `9dfec62` (add the update wrapper).

## ULSBS documentation

Use this README for the Unilaiva/Astral repository's workflow. ULSBS's own
documentation is organized by task:

- [ULSBS README](https://github.com/unilaiva/ulsbs/blob/main/README.md): features,
  independent-project setup, compilation, variants and editions, configuration, and utilities.
- [Writing Songbooks](https://github.com/unilaiva/ulsbs/blob/main/WRITING_SONGBOOKS.md):
  song syntax, LilyPond scores, metadata, tags, indices, selections, and layout customization.
- [Configuration example](https://github.com/unilaiva/ulsbs/blob/main/ulsbs-config-example.toml):
  the annotated build-setting and profile reference. This repository uses its own
  [`ulsbs-config.toml`](ulsbs-config.toml), not that example file.
- [Editor support](https://github.com/unilaiva/ulsbs/blob/main/vscode-extension/ulsbs-tex-tools/README.md):
  VS Code extension installation and use.
- [Architecture](https://github.com/unilaiva/ulsbs/blob/main/ARCHITECTURE.md):
  engine internals, PDF/viewer contracts, cache maintenance, and developer testing.

These documents are also available locally under `ulsbs/`, matching the engine
revision checked out by this repository. The online links follow ULSBS's `main`
branch and may describe a newer revision.

## Status

ULSBS is under active development, and this repository tracks its current
behavior. Review the [ULSBS changelog](https://github.com/unilaiva/ulsbs/blob/main/CHANGELOG.md)
when updating the engine. Until a stable 1.0 release, external songbook projects
may need to adjust their sources when upgrading.

## Contact

For help with the songbooks or compilation, song corrections, or other questions,
you are welcome to contact **Lari Natri** by email. You can find the address in
the copyright header at the top of e.g.
[this source file](include/ulsbs-songbook-unilaiva-default.cls).
You do not need to open a GitHub issue to ask for help; email is welcome too.

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
