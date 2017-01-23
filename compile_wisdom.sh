#!/bin/sh
#
# This UNIX shell script compiles wisdom-songbook.tex using pdflatex to produce
# wisdom-songbook.pdf. Song indexes are created, if the binary songidx is found
# in projects subdirectory ext_packages/bin/

SONGIDXPROG="ext_packages/bin/songidx"

die() {
  echo "$2" >&2
  exit $1
}

which "pdflatex" >"/dev/null" || die 1 "pdflatex program not found! Aborting."

pdflatex -interaction=nonstopmode wisdom-songbook.tex || die $? "Compilation error!" # first run 

if [ -x "$SONGIDXPROG" ]; then
  "$SONGIDXPROG" idx_wisdom-sb_title.sxd idx_wisdom-sb_title.sbx
  "$SONGIDXPROG" idx_wisdom-sb_auth.sxd idx_wisdom-sb_auth.sbx
  # bin/songidx idx_wisdom-sb_scrip.sxd idx_wisdom-sb_scrip.sbx
  pdflatex -interaction=nonstopmode wisdom-songbook.tex # second run
  ecode=$?
  # Copy compiled PDF to a specific directory if user is larva. Sorry for this. :)
  if [ $ecode -eq 0 ] && [ "$USER" = "larva" ] && [ -d "/home/larva/Cloud/ownCloud/wisdom" ]; then
    cp wisdom-songbook.pdf "/home/larva/Cloud/ownCloud/wisdom/"
    if [ $? -eq 0 ]; then echo "Compiled PDF copied to 'the cloud'"; fi
  fi
  exit $ecode
else
  echo "$SONGIDXPROG not found. Indexes not created!"
fi


