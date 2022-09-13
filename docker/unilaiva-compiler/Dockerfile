# Dockerfile for compiling Unilaiva songbook
# ==========================================
#
# Run this image with "compile-songbooks.sh", as that script will
# setup the *required* bind mount and use correct user id.
#

# Use Ubuntu 22.04 LTS:
FROM ubuntu:jammy-20220815

# Installs everything needed for compiling the songbook, plus qrencode and
# pdftk utilities. Also generates the required locale fi_FI.utf8.
RUN apt-get update \
  && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    bash \
    locales \
    context \
    context-modules \
    fonts-noto-extra \
    fonts-noto-color-emoji \
    fonts-noto-core \
    fonts-noto-mono \
    lilypond \
    texlive \
    texlive-font-utils \
    texlive-lang-arabic \
    texlive-lang-english \
    texlive-lang-european \
    texlive-latex-base \
    texlive-latex-extra \
    texlive-luatex \
    texlive-music \
    texlive-plain-generic \
    # pdftk \
    qrencode \
  && rm -rf /var/lib/apt/lists/*

# Enlarge the available memory available to some TeX engines. (Some
# ul-selection*.tex files have a problem with too small main memory on such
# engines). This does not affect lua(la)tex, our default engine, but left
# here for compatibility with other engines.
COPY 99-tex-max-memory.cnf /etc/texmf/texmf.d/

# 1. Generate Finnish locale, which is used for sorting indices by default.
# Finnish alphabet is a superset of English, so this does not need to be changed
# for English-only books.
# 2. Create index databases used by TeX
RUN locale-gen fi_FI.utf8 \
  && update-texmf \
  && texhash \
  && luaotfload-tool --update

# Setup a non-root user for everything. Make it's home world-writable so that
# we can use host machine's user id and still have access to container's
# ~/.texlive2020 when compiling.
RUN useradd --create-home --shell /bin/bash unilaiva \
  && chmod 777 /home/unilaiva

USER unilaiva

ENV HOME="/home/unilaiva" \
    IN_UNILAIVA_DOCKER_CONTAINER="true"

# Make "/home/unilaiva" a volume to make texmf cache within it persistent for a
# slight performance boost. Otherwise it is just generated each time on demand.
# "/unilaiva-songbook" is the directory where songbook data is expected, and it
# is to be bind mounted from the host (by the compile script)
VOLUME ["/home/unilaiva", "/unilaiva-songbook"]

WORKDIR /unilaiva-songbook

# Located on the bind mount
ENTRYPOINT ["./compile-songbooks.sh"]
