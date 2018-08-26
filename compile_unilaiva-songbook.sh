#!/bin/sh
#
# This UNIX shell script compiles unilaiva-songbook.tex using different
# tools to produce unilaiva-songbook.pdf
#
# Usage: run without argument for default operation. See function print_usage_and_exit
# below for further information.
#
# Required binaries in PATH: lilypond-book, pdflatex, texlua
# Optional binary in PATH: context (will be used to create printout versions)
#


SONG_IDX_SCRIPT="ext_packages/songs/songidx.lua"
MAIN_TEX_FILE="unilaiva-songbook.tex"
TEMP_DIRNAME="temp" # just the name of a subdirectory, not an absolute path

initial_dir="$PWD"

# Function: print the program usage informationand exit.
print_usage_and_exit() {
  echo "Usage: compile_unilaiva-songbook.sh [--no-deploy]"
  echo ""
  echo "If the optional --no-deploy argument is not present, the resulting"
  echo "PDF files will also be copied to ./deploy/ directory (if it exists)."
  exit 1
}

# Function: exit the program with error code and message.
# Usage: die <errorcode> <message>
die() {
  echo "$2" >&2
  cd "$initial_dir"
  exit $1
}

# Test program arguments
deployfinal="true"
if [ "$#" -gt "0" ]; then
  [ "$#" -gt "1" ] && print_usage_and_exit
  [ "$1" != "--no-deploy" ] && print_usage_and_exit
  deployfinal="false"
fi

# Test if we are currently in the correct directory:
[ -f "./unilaiva-songbook.tex" ] || die 1 "Not currently in the repository root directory! Aborted."

# Test executable availability:
which "pdflatex" >"/dev/null" || die 1 "pdflatex binary not found in path! Aborted."
which "texlua" >"/dev/null" || die 1 "texlua binary not found in path! Aborted."
which "lilypond-book" >"/dev/null" || die 1 "lilypond-book binary not found in path! Aborted."

echo "\nSTART lilypond (lilypond-book)\n"

# Run lilypond-book. It compiles images out of lilypond source code within tex files and outputs
# the modified .tex files and the musical shaft images created by it to subdirectory $TEMP_DIRNAME.
# The directory is created if it doesn't exist.
lilypond-book -f latex --output $TEMP_DIRNAME "$MAIN_TEX_FILE" || die $? "Error running lilypond-book! Aborted."

# Enter the temp directory. (Do rest of the steps there.)
cd "$TEMP_DIRNAME" || die 1 "Cannot enter temporary directory! Aborted."
# Link the required files that lilypond hasn't copied to the temp directory:
ln -s "../ext_packages" "./" 2>"/dev/null"
ln -s "../../content/img" "./content/" 2>"/dev/null"  # because lilypond doesn't copy the included images
ln -s "../tags.can" "./" 2>"/dev/null"

echo "\nSTART pdflatex 1st run\n"

# First run of pdflatex:
pdflatex -interaction=nonstopmode $MAIN_TEX_FILE || die $? "Compilation error running pdflatex! Aborted."

echo "\nSTART index creation (texlua)\n"

# Create indices:
"texlua" "$SONG_IDX_SCRIPT" idx_unilaiva-songbook_title.sxd idx_unilaiva-songbook_title.sbx || die $? "Error creating song title indices! Aborted."
echo ""
# Author index creation is commented out, as it is not used (now):
# "texlua" "$SONG_IDX_SCRIPT" idx_unilaiva-songbook_auth.sxd idx_unilaiva-songbook_auth.sbx || die $? "Error creating author indices! Aborted."
"texlua" "$SONG_IDX_SCRIPT" -b tags.can idx_unilaiva-songbook_tag.sxd idx_unilaiva-songbook_tag.sbx || die $? "Error creating tag (scripture) indices! Aborted."

echo "\nSTART pdflatex 2nd run\n"

# Second run of pdflatex, creates the final main PDF document:
pdflatex -interaction=nonstopmode $MAIN_TEX_FILE
[ $? -eq 0 ] || die $ecode "Compilation error running pdflatex (2nd time)! Aborted."

cp "unilaiva-songbook.pdf" "../" || die $? "Error copying unilaiva-songbook.pdf from temporary directory! Aborted."

echo "\nSTART printout creation (context)\n"

# Create printouts, if context binary is found:
printouts_created="false"
which "context" >"/dev/null"
if [ $? -eq 0 ]; then
  context "../printout_unilaiva-songbook_A5_on_A4_doublesided_folded.context" && context "../printout_unilaiva-songbook_A5_on_A4_sidebyside_simple.context" && printouts_created="true"
  cp printout*.pdf "../" || die $? "Error copying printout PDFs from temporary directory! Aborted."
else
  echo "Extra printout PDFs not created, because 'context' binary not found."
fi

# Clean up the temporary directory: remove some temporary files.
rm tmp*.out tmp*.sxc 2>"/dev/null"

# Get out of $TEMP_DIRNAME:
cd "$initial_dir" || die $? "Cannot return to the main directory."

echo "\n"

# If "--no-deploy" is not given as an argument and the subdirectory 'deploy' exists, copy the
# final PDFs there also. (The directory is meant to be automatically synced to the server by
# other means.)
if [ "$deployfinal" = "true" ] && [ -d "./deploy" ]; then
  cp "unilaiva-songbook.pdf" "./deploy/" && echo "Deploy: unilaiva-songbook.pdf copied to ./deploy/"
  if [ "$printouts_created" = "true" ]; then
    cp printout*.pdf "./deploy/" && echo "Deploy: extra printouts copied to ./deploy/"
  fi
else
  echo "(Deploy: resulting files not copied to the deploy directory.)"
fi

echo "\nCompilation succesful! Enjoy your unilaiva-songbook.pdf\n"

exit 0
