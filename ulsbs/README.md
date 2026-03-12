# ULSBS

This package provides the ULSBS compiler CLI (`ulsbs-compile`) used to build
LuaLaTeX + lilypond-book based songbooks.

- Runs in Docker by default (builds/updates image as needed)
- `--no-docker` runs on the host (not recommended unless your host toolchain matches)

This repository is intended to be used as a standalone engine that multiple songbook
collections can depend on.
