# SPDX-FileCopyrightText: 2016-2026 Lari Natri <lari.natri@iki.fi>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Dockerfile for compiling ULSBS songbooks
# ========================================
#
# Works with docker and podman.
#
# Containers created from the image described here is intended to be only run
# with "ulsbs-compile" script, as that script will setup the *required* bind
# mounts, use the correct user id from host etc.
#
# This file is part of the 'ulsbs' package.

# Use Ubuntu 24.04 LTS:
FROM ubuntu:questing-20251217

# Installs everything needed for compiling the songbook, plus qrencode and
# pdftk utilities. Also generates the required locale fi_FI.utf8.
RUN apt-get update \
  && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    bash \
    locales \
    context \
    context-modules \
    ffmpeg \
    fluidsynth \
    fluid-soundfont-gm \
    fonts-noto-extra \
    #fonts-noto-color-emoji \
    fonts-noto-core \
    fonts-noto-mono \
    imagemagick \
    lilypond \
    poppler-utils \
    python3 \
    texlive \
    texlive-font-utils \
    texlive-lang-arabic \
    texlive-lang-english \
    texlive-lang-european \
    texlive-lang-portuguese \
    texlive-lang-spanish \
    texlive-latex-base \
    texlive-latex-extra \
    texlive-luatex \
    texlive-music \
    texlive-plain-generic \
    #pdftk \
    qrencode \
  && rm -rf /var/lib/apt/lists/*

# Enlarge the available memory available to some TeX engines. (Some
# ul-selection*.tex files have a problem with too small main memory on such
# engines). This does not affect lua(la)tex, our default engine, but left
# here for compatibility with other engines.
COPY 99-tex-max-memory.cnf /etc/texmf/texmf.d/

# Copy a minimal client config for Pipewire, as that will make fluidsynth's
# logging happy. We are not really using Pipewire.
RUN mkdir -p /etc/pipewire
COPY pipewire-client.conf /etc/pipewire/client.conf

# 1. Generate Finnish locale, which is used for sorting indices by default.
# Finnish alphabet is a superset of English, so this does not need to be changed
# for English-only books.
# 2. Setup a non-root user for everything. Make it's home world-writable so that
#    we can use host machine's user id and still have access to container's
#    ~/.texlive20?? when compiling.
RUN locale-gen fi_FI.utf8 \
  && useradd --create-home --shell /bin/bash ulsbs \
  && chmod 777 /home/ulsbs \
  && chmod g+s /home/ulsbs

# Create index databases and caches used by Tex and Lilypond
RUN update-texmf \
  && mtxrun --generate \
  && texhash \
  && fc-cache -f \
  && luaotfload-tool --update

ARG BUILT_BY_ULSBS_VERSION
LABEL built.by.ulsbs.version=$BUILT_BY_ULSBS_VERSION

USER ulsbs

ENV HOME="/home/ulsbs" \
    ULSBS_INTERNAL_RUNNING_IN_CONTAINER="true"

# Create user caches and make world-writeable to be used with host machine's
# user id:
RUN fc-cache -f \
  && luaotfload-tool --update \
  && lilypond -dshow-available-fonts >/dev/null \
  && find /home/ulsbs -type d -exec chmod 777 {} + \
  && find /home/ulsbs -type f -exec chmod 666 {} +

# Make "/home/ulsbs" a volume to make caches within it persistent for a
# slight performance boost. Otherwise it is just generated each time on demand.
VOLUME ["/home/ulsbs"]

WORKDIR /songbook-data

# Default command for interactive use; the host-side launcher will override it.
CMD ["bash"]
