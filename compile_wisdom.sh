#!/bin/sh
#
# This UNIX shell script compiles wisdom-songbook.tex using different
# tools to produce wisdom-songbook.pdf
#
# Required binaries in PATH: lilypond-book, pdflatex
# Required manually compiled binary: ext_packages/bin/songidx


SONG_IDX_PROG="ext_packages/bin/songidx"
MAIN_TEX_FILE="wisdom-songbook.tex"
TEMP_DIRNAME="compile_temp" # just the name of a subdirectory, not an absolute path

die() {
  echo "$2" >&2
  exit $1
}

which "pdflatex" >"/dev/null" || die 1 "pdflatex binary not found in path! Aborted."
which "lilypond-book" >"/dev/null" || die 1 "lilypond-book binary not found in path! Aborted."
which "$SONG_IDX_PROG" >"/dev/null" || die 1 "$SONG_IDX_PROG binary not found! Aborted."

# Run lilypond-book. It compiles images out of lilypond source code within tex files and outputs
# the modified .tex files and the images to subdirectory $TEMP_DIRNAME
lilypond-book -f latex --output $TEMP_DIRNAME "$MAIN_TEX_FILE" || die $? "Error running lilypond-book! Aborted."

# go to the temp directory to do rest of the steps there
cd $TEMP_DIRNAME
ln -s "../ext_packages" "./" 2>"/dev/null"
ln -s "../../content/img" "./content/" 2>"/dev/null"

# first run of pdflatex
pdflatex -interaction=nonstopmode $MAIN_TEX_FILE || die $? "Compilation error running pdflatex! Aborted."

echo ""

# create indeces    
"$SONG_IDX_PROG" idx_wisdom-sb_title.sxd idx_wisdom-sb_title.sbx || die $? "Error creating song title indeces! Aborted."
echo ""
"$SONG_IDX_PROG" idx_wisdom-sb_auth.sxd idx_wisdom-sb_auth.sbx || die $? "Error creating author indeces! Aborted."
# "$SONG_IDX_PROG" idx_wisdom-sb_scrip.sxd idx_wisdom-sb_scrip.sbx || die $? "Error creating scripture indeces! Aborted."

echo ""

# second run of pdflatex, creates the final PDF document
pdflatex -interaction=nonstopmode $MAIN_TEX_FILE 
ecode=$?

cd .. # get out of $TEMP_DIRNAME
cp $TEMP_DIRNAME/wisdom-songbook.pdf ./ 

[ $ecode -eq 0 ] || die $ecode "Compilation error running pdflatex (2nd time)! Aborted."

echo ""

# If subdirectory 'deploy' exists, copy the PDF there also.
if [ -d "./deploy" ]; then
  cp "wisdom-songbook.pdf" "./deploy/" && echo "Compiled PDF copied to ./deploy/"
else
  echo "PDF not deployed"
fi

echo "Compilation succesful. Enjoy your wisdom-songbook.pdf"

exit 0
