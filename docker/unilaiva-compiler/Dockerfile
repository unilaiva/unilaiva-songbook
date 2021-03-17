# Dockerfile for compiling Unilaiva songbook
# ==========================================
#
# Run this image with "compile_unilaiva-songbook.sh", as that script will
# setup the *required* bind mount and use correct user id.
#

# Note that Ubuntu 20.04 Focal has a problem with Noto Medium; that's why we
# use non-LTS 20.10 Groovy.
FROM ubuntu:groovy-20210225

# Installs everything needed for compiling the songbook, plus qrencode and
# pdftk utilities. Also generates the required locale fi_FI.utf8.
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
    texlive-music \
    texlive-plain-generic \
    qrencode \
    pdftk \
  && rm -rf /var/lib/apt/lists/*
RUN locale-gen fi_FI.utf8

# Enlarge the available memory available to TeX (some ul-selection*.tex files
# have a problem with too small main memory):
COPY 99-tex-max-memory.cnf /etc/texmf/texmf.d/
RUN update-texmf \
  && texhash

# Setup a non-root user for everything. Make it's home world-writable so that
# we can use host machine's user id and still have access to container's
# ~/.texlive2020 when compiling.
RUN useradd --create-home --shell /bin/bash unilaiva && chmod 777 /home/unilaiva

USER unilaiva

ENV HOME="/home/unilaiva" \
    IN_UNILAIVA_DOCKER_CONTAINER="true"

# Make this a volume to make texmf cache within it persistent for a slight
# performance boost. Otherwise it is just generated each time on demand.
VOLUME /home/unilaiva

# This must be bind mounted from the host
VOLUME /unilaiva-songbook

WORKDIR /unilaiva-songbook

# Located on the bind mount
ENTRYPOINT ["./compile_unilaiva-songbook.sh"]
