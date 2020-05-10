# Dockerfile for compiling Unilaiva songbook
# ==========================================
#
# Run this image with "compile_unilaiva-songbook.sh --docker", as that script
# will setup the *required* bind mount and use correct user id.
#

FROM ubuntu:bionic-20200403

RUN apt-get update \
  && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    locales \
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

# Setup context
ENV TEXMFCACHE=/texmf-cache
RUN mkdir /texmf-cache \
  && chmod 777 /texmf-cache \
  && mtxrun --generate \
  && context --make

# This must be bind mounted from the host
VOLUME /unilaiva-songbook

WORKDIR /unilaiva-songbook

# This is required for the compile script to not create
# infinite nested containers :)
ENV IN_UNILAIVA_DOCKER_CONTAINER=true

# Located on the bind mount
ENTRYPOINT ["./compile_unilaiva-songbook.sh"]
