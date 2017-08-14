#!/bin/sh
#
# This UNIX shell script compiles unilaiva-songbook.tex using different
# tools to produce unilaiva-songbook.pdf
#
# Required binaries in PATH: lilypond-book, pdflatex, texlua
#
# Optional binary in PATH: context (will be used to create printouts)
#


SONG_IDX_SCRIPT="ext_packages/songs/songidx.lua"
MAIN_TEX_FILE="unilaiva-songbook.tex"
TEMP_DIRNAME="temp" # just the name of a subdirectory, not an absolute path

initial_dir="$PWD"

die() {  # Usage: die <errorcode> <message>
  echo "$2" >&2
  cd "$initial_dir"
  exit $1
}

# Test if we are currently in the correct directory:
[ -f "./unilaiva-songbook.tex" ] || die 1 "Not currently in the repository root directory! Aborted."

# Test executable availability
which "pdflatex" >"/dev/null" || die 1 "pdflatex binary not found in path! Aborted."
which "texlua" >"/dev/null" || die 1 "texlua binary not found in path! Aborted."
which "lilypond-book" >"/dev/null" || die 1 "lilypond-book binary not found in path! Aborted."

# Run lilypond-book. It compiles images out of lilypond source code within tex files and outputs
# the modified .tex files and the images to subdirectory $TEMP_DIRNAME
lilypond-book -f latex --output $TEMP_DIRNAME "$MAIN_TEX_FILE" || die $? "Error running lilypond-book! Aborted."

# go to the temp directory to do rest of the steps there
cd $TEMP_DIRNAME
ln -s "../ext_packages" "./" 2>"/dev/null"
ln -s "../../content/img" "./content/" 2>"/dev/null"
ln -s "../tags.can" "./" 2>"/dev/null"

# first run of pdflatex
pdflatex -interaction=nonstopmode $MAIN_TEX_FILE || die $? "Compilation error running pdflatex! Aborted."

echo ""

# create indices
"texlua" "$SONG_IDX_SCRIPT" idx_unilaiva-songbook_title.sxd idx_unilaiva-songbook_title.sbx || die $? "Error creating song title indeces! Aborted."
echo ""
"texlua" "$SONG_IDX_SCRIPT" idx_unilaiva-songbook_auth.sxd idx_unilaiva-songbook_auth.sbx || die $? "Error creating author indeces! Aborted."
"texlua" "$SONG_IDX_SCRIPT" -b tags.can idx_unilaiva-songbook_tag.sxd idx_unilaiva-songbook_tag.sbx || die $? "Error creating tag (scripture) indeces! Aborted."

echo ""

# second run of pdflatex, creates the final PDF document
pdflatex -interaction=nonstopmode $MAIN_TEX_FILE 
[ $? -eq 0 ] || die $ecode "Compilation error running pdflatex (2nd time)! Aborted."

echo ""

# Create printouts, if context binary is found:
printouts_created=0
which "context" >"/dev/null"
if [ $? -eq 0 ]; then
  context "../printout_unilaiva-songbook_A5_on_A4_doublesided_folded.context" && context "../printout_unilaiva-songbook_A5_on_A4_sidebyside_simple.context" && printouts_created="yes"
else
  echo "Extra printout PDFs not created, because 'context' program not found."
fi

cd "$initial_dir" # get out of $TEMP_DIRNAME
cp "$TEMP_DIRNAME/"*.pdf "./" || die $? "Error copying result files from temporary directory! Aborted."

echo ""

# If subdirectory 'deploy' exists, copy the PDFs there also.
if [ -d "./deploy" ]; then
  cp "unilaiva-songbook.pdf" "./deploy/" && echo "Compiled PDF copied to ./deploy/"
  if [ "$printouts_created" = "yes" ]; then
    cp printout*.pdf "./deploy/" && echo "Extra printouts copied to ./deploy/"
  fi
else
  echo "PDF not deployed"
fi

echo "Compilation succesful. Enjoy your unilaiva-songbook.pdf"

exit 0
