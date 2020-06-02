# Dockerfile for compiling Unilaiva songbook
# ==========================================
#
# Run this image with "compile_unilaiva-songbook.sh --docker", as that script
# will setup the *required* bind mount and use correct user id.
#

# 19.10 Eoan seems to be the newest image that works with Noto Medium;
# one could use 18.04 LTS Bionic here as well, but we chose Eoan, because it
# has newer TeX packages, and we don't really need the latest security updates.
FROM ubuntu:eoan-20200410

RUN apt-get update \
  && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    locales \
    git \
    context \
    context-modules \
    lilypond \
    texlive \
    texlive-fonts-extra \
    texlive-font-utils \
    texlive-lang-english \
    texlive-lang-european \
    texlive-latex-extra \
  && rm -rf /var/lib/apt/lists/*

# Generate the required locale
RUN locale-gen fi_FI.utf8

# Setup a non-root user for everything. Make it's home world-writable so that
# we can use host machine's user id and still have access to container's
# ~/.texlive2019 when compiling.
RUN useradd --create-home --shell /bin/bash unilaiva && chmod 777 /home/unilaiva
USER unilaiva
ENV HOME=/home/unilaiva

# Make this a volume to make texmf cache within it persistent for a slight
# performance boost. Otherwise it is just generated each time on demand.
VOLUME /home/unilaiva

# This must be bind mounted from the host
VOLUME /unilaiva-songbook

WORKDIR /unilaiva-songbook

# This is required for the compile script to not create
# infinite nested containers :)
ENV IN_UNILAIVA_DOCKER_CONTAINER=true

# Located on the bind mount
ENTRYPOINT ["./compile_unilaiva-songbook.sh"]
