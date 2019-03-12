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


MAIN_FILENAME_BASE="unilaiva-songbook" # filename base for the main document (without .tex suffix)
TEMP_DIRNAME="temp" # just the name of a subdirectory, not an absolute path
SONG_IDX_SCRIPT="ext_packages/songs/songidx.lua"

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
  cd "${initial_dir}"
  exit $1
}

# Function: compile the document given as parameter
# Usage: compile_document <filename_base_for_tex_document> # without .tex suffix
compile_document() {

  document_basename="$1"
  
  # Test if we are currently in the correct directory:
  [ -f "./${document_basename}.tex" ] || die 1 "Not currently in the project's root directory! Aborted."
  [ "${initial_dir##*/}" = "${TEMP_DIRNAME}" ] && die 1 "You seem to be in the temp directory instead of the project's root! Aborted."

  echo "\nSTART lilypond (lilypond-book)\n"

  # Run lilypond-book. It compiles images out of lilypond source code within tex files and outputs
  # the modified .tex files and the musical shaft images created by it to subdirectory ${TEMP_DIRNAME}.
  # The directory is created if it doesn't exist.
  lilypond-book -f latex --output "${TEMP_DIRNAME}" "${document_basename}.tex" || die $? "Error running lilypond-book! Aborted."

  # Enter the temp directory. (Do rest of the steps there.)
  cd "${TEMP_DIRNAME}" || die 1 "Cannot enter temporary directory! Aborted."
  # Link the required files that lilypond hasn't copied to the temp directory:
  ln -s "../ext_packages" "./" 2>"/dev/null"
  ln -s "../../content/img" "./content/" 2>"/dev/null"  # because lilypond doesn't copy the included images
  ln -s "../tags.can" "./" 2>"/dev/null"

  echo "\nSTART pdflatex 1st run\n"

  # First run of pdflatex:
  pdflatex -interaction=nonstopmode "${document_basename}.tex" || die $? "Compilation error running pdflatex! Aborted."

  echo "\nSTART index creation (texlua)\n"

  # Create indices:
  texlua "${SONG_IDX_SCRIPT}" "idx_${document_basename}_title.sxd" "idx_${document_basename}_title.sbx" || die $? "Error creating song title indices! Aborted."
  echo ""
  # Author index creation is commented out, as it is not used (now):
  # texlua "${SONG_IDX_SCRIPT}" idx_${document_basename}_auth.sxd idx_${document_basename}_auth.sbx || die $? "Error creating author indices! Aborted."
  texlua "${SONG_IDX_SCRIPT}" -b "tags.can" "idx_${document_basename}_tag.sxd" "idx_${document_basename}_tag.sbx" || die $? "Error creating tag (scripture) indices! Aborted."

  echo "\nSTART pdflatex 2nd run\n"

  # Second run of pdflatex, creates the final main PDF document:
  pdflatex -interaction=nonstopmode "${document_basename}.tex"
  [ $? -eq 0 ] || die $ecode "Compilation error running pdflatex (2nd time)! Aborted."

  cp "${document_basename}.pdf" "../" || die $? "Error copying ${document_basename}.pdf from temporary directory! Aborted."

  echo "\nSTART printout creation (context)\n"

  # Create printouts, if context binary is found:
  printouts_created="false"
  which "context" >"/dev/null"
  if [ $? -eq 0 ]; then
    context "../printout_${document_basename}_A5_on_A4_doublesided_folded.context" && context "../printout_${document_basename}_A5_on_A4_sidebyside_simple.context" && printouts_created="true"
    cp printout*.pdf "../" || die $? "Error copying printout PDFs from temporary directory! Aborted."
  else
    echo "Extra printout PDFs not created, because 'context' binary not found."
  fi

  # Clean up the temporary directory: remove some temporary files.
  rm tmp*.out tmp*.sxc 2>"/dev/null"

  # Get out of ${TEMP_DIRNAME}:
  cd "${initial_dir}" || die $? "Cannot return to the main directory."

  echo "\n"

  # If "--no-deploy" is not given as an argument and the subdirectory 'deploy' exists, copy the
  # final PDFs there also. (The directory is meant to be automatically synced to the server by
  # other means.)
  if [ "$deployfinal" = "true" ] && [ -d "./deploy" ]; then
    cp "${document_basename}.pdf" "./deploy/" && echo "Deploy: ${document_basename}.pdf copied to ./deploy/"
    if [ "$printouts_created" = "true" ]; then
      cp printout*.pdf "./deploy/" && echo "Deploy: extra printouts copied to ./deploy/"
    fi
  else
    echo "(Deploy: resulting files not copied to the deploy directory.)"
  fi

  echo "\nCompilation succesful! Enjoy your ${document_basename}.pdf\n"

} # END compile_document()


# Test program arguments
deployfinal="true"
if [ "$#" -gt "0" ]; then
  [ "$#" -gt "1" ] && print_usage_and_exit
  [ "$1" != "--no-deploy" ] && print_usage_and_exit
  deployfinal="false"
fi

# Test executable availability:
which "pdflatex" >"/dev/null" || die 1 "pdflatex binary not found in path! Aborted."
which "texlua" >"/dev/null" || die 1 "texlua binary not found in path! Aborted."
which "lilypond-book" >"/dev/null" || die 1 "lilypond-book binary not found in path! Aborted."


# Compile the main document (defined at the top of this file):
compile_document "${MAIN_FILENAME_BASE}"


exit 0
