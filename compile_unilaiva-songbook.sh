#!/bin/sh
#
# This UNIX shell script compiles unilaiva-songbook.tex using different
# tools to produce unilaiva-songbook.pdf
#
# Usage: run without argument for default operation. Run with --help argument
# for further information about options, or see function print_usage_and_exit
# below.
#
# Required binaries in PATH: lilypond-book, pdflatex, texlua
# Optional binary in PATH: context (will be used to create printout versions)
#


MAIN_FILENAME_BASE="unilaiva-songbook" # filename base for the main document (without .tex suffix)
PART1_FILENAME_BASE="unilaiva-songbook_part1" # filename base for the 2-part document's part 1 (without .tex suffix)
PART2_FILENAME_BASE="unilaiva-songbook_part2" # filename base for the 2-part document's part 2 (without .tex suffix)
TEMP_DIRNAME="temp" # just the name of a subdirectory, not an absolute path
SONG_IDX_SCRIPT="ext_packages/songs/songidx.lua"

initial_dir="$PWD"

# Function: print the program usage informationand exit.
print_usage_and_exit() {
  echo ""
  echo "Usage: compile_unilaiva-songbook.sh [options]"
  echo ""
  echo "Options:"
  echo ""
  echo "  --no-partial   : do not compile partial books, only the main document"
  echo "  --no-printouts : do not create extra printout PDFs"
  echo "  --no-deploy    : do not copy PDF files to ./deploy/"
  echo "  -d             : all of the above options"
  echo ""
  echo "In addition to the full songbook, also two-booklet version is created,"
  echo "with parts 1 and 2 in separate PDFs. This is not done, if --no-partial"
  echo "option is present."
  echo ""
  echo "Special versions for printing (printout_unilaiva-songbook_*.pdf) are"
  echo "created, if 'context' binary is available and --no-printouts option"
  echo "is not given."
  echo ""
  echo "If --no-deploy argument is not present, the resulting PDF files will"
  echo "also be copied to ./deploy/ directory (if it exists)."
  echo ""
  exit 1
}

# Function: exit the program with error code and message.
# Usage: die <errorcode> <message>
die() {
  echo "\nERROR: $2" >&2
  cd "${initial_dir}"
  exit $1
}

# Function: compile the document given as parameter
# Usage: compile_document <filename_base_for_tex_document> # without path and without ".tex" suffix
compile_document() {

  # Usage: die_log <errorcode> <message> <logfile>
  die_log() {
    echo "  ERROR: $2"
    echo "\nDisplaying log file for ${document_basename}.tex: $3\n"
    cat "$3"
    die $1 "$2"
  }

  document_basename="$1"
  temp_dirname_twolevels="${TEMP_DIRNAME}/${document_basename}"

  # Test if we are currently in the correct directory:
  [ -f "./${document_basename}.tex" ] || die 1 "Not currently in the project's root directory! Aborted."
  [ -f "./compile_unilaiva-songbook.sh" ] || die 1 "Not currently in the project's root directory! Aborted."

  # Clean old build:
  rm -R "${temp_dirname_twolevels}" 2>"/dev/null" # Clean old build
  mkdir -p "${temp_dirname_twolevels}" 2>"/dev/null" || die $? "Could not create the build directory ${temp_dirname_twolevels}. Aborted."

  echo "\nCompiling ${document_basename}.tex ..."

  echo "  EXEC: lilypond (lilypond-book)"

  # Run lilypond-book. It compiles images out of lilypond source code within tex files and outputs
  # the modified .tex files and the musical shaft images created by it to subdirectory ${temp_dirname_twolevels}.
  # The directory is created if it doesn't exist.
  lilypond-book -f latex --output "${temp_dirname_twolevels}" "${document_basename}.tex" 1>"${temp_dirname_twolevels}/out-1_lilypond.log" 2>&1 || die_log $? "Error running lilypond-book! Aborted." "${temp_dirname_twolevels}/out-1_lilypond.log"

  # Enter the temp directory. (Do rest of the steps there.)
  cd "${temp_dirname_twolevels}" || die 1 "Cannot enter temporary directory! Aborted."
  # Link the required files that lilypond hasn't copied to the temp directory:
  ln -s "../../../tex/unilaiva-songbook_common.sty" "./tex/" 2>"/dev/null"
  ln -s "../../ext_packages" "./" 2>"/dev/null"
  ln -s "../../../content/img" "./content/" 2>"/dev/null"  # because lilypond doesn't copy the included images
  ln -s "../../tags.can" "./" 2>"/dev/null"

  echo "  EXEC: pdflatex (1st run)"

  # First run of pdflatex:
  pdflatex -interaction=nonstopmode "${document_basename}.tex" 1>"out-2_pdflatex.log" 2>&1 || die_log $? "Compilation error running pdflatex! Aborted." "out-2_pdflatex.log"

  echo "  EXEC: texlua (create indices)"

  # Create indices:
  texlua "${SONG_IDX_SCRIPT}" "idx_${document_basename}_title.sxd" "idx_${document_basename}_title.sbx" 1>"out-3_titleidx.log" 2>&1 || die_log $? "Error creating song title indices! Aborted." "out-3_titleidx.log"
  # Author index creation is commented out, as it is not used (now):
  # texlua "${SONG_IDX_SCRIPT}" idx_${document_basename}_auth.sxd idx_${document_basename}_auth.sbx 1>"out-4_authidx.log" 2>&1 || die_log $? "Error creating author indices! Aborted." "out-4_authidx.log"
  texlua "${SONG_IDX_SCRIPT}" -b "tags.can" "idx_${document_basename}_tag.sxd" "idx_${document_basename}_tag.sbx" 1>"out-5_tagidx.log" 2>&1 || die_log $? "Error creating tag (scripture) indices! Aborted." "out-5_tagidx.log"

  echo "  EXEC: pdflatex (2nd run)"

  # Second run of pdflatex, creates the final main PDF document:
  pdflatex -interaction=nonstopmode "${document_basename}.tex" 1>"out-6_pdflatex.log" 2>&1 || die_log $? "Compilation error running pdflatex (2nd time)! Aborted." "out-6_pdflatex.log"

  echo "  EXEC: pdflatex (3rd run)"

  # Third run of pdflatex, creates the final main PDF document:
  pdflatex -interaction=nonstopmode "${document_basename}.tex" 1>"out-7_pdflatex.log" 2>&1 || die_log $? "Compilation error running pdflatex (2nd time)! Aborted." "out-7_pdflatex.log"

  cp "${document_basename}.pdf" "../../" || die $? "Error copying ${document_basename}.pdf from temporary directory! Aborted."

  overfull_count=$(grep -i overfull "out-7_pdflatex.log" | wc -l)
  underfull_count=$(grep -i underfull "out-7_pdflatex.log" | wc -l)
  [ "${overfull_count}" -gt "0" ] && echo "  DEBUG: Overfull warnings: ${overfull_count}"
  [ "${underfull_count}" -gt "0" ] && echo "  DEBUG: Underfull warnings: ${underfull_count}"

  # Create printouts, if context binary is found:
  printouts_created="false"
  if [ ${createprintouts} = "true" ]; then
    which "context" >"/dev/null"
    if [ $? -eq 0 ]; then
      echo "  EXEC: context (create printouts)"
      context "../../tex/printout_${document_basename}_A5_on_A4_doublesided_folded.context" 1>"out-7_printout-dsf.log" 2>&1 || die_log $? "Error creating dsf printout! Aborted." "out-8_printout-dsf.log"
      context "../../tex/printout_${document_basename}_A5_on_A4_sidebyside_simple.context" 1>"out-8_printout-sss.log" 2>&1 || die_log $? "Error creating sss printout! Aborted." "out-9_printout-sss.log"
      printouts_created="true"
      cp printout*.pdf "../../" || die $? "Error copying printout PDFs from temporary directory! Aborted."
    else
      echo "  NOEXEC: Extra printout PDFs not created, because 'context' binary not found."
    fi
  else
    echo "  NOEXEC: Extra printout PDFs not created."
  fi

  # Clean up the temporary directory: remove some temporary files.
  rm tmp*.out tmp*.sxc 2>"/dev/null"

  # Get out of ${temp_dirname_twolevels}:
  cd "${initial_dir}" || die $? "Cannot return to the main directory."

  # If "--no-deploy" is not given as an argument and the subdirectory 'deploy' exists, copy the
  # final PDFs there also. (The directory is meant to be automatically synced to the server by
  # other means.)
  if [ "${deployfinal}" = "true" ] && [ -d "./deploy" ]; then
    cp "${document_basename}.pdf" "./deploy/" && echo "  DEPLOY: ${document_basename}.pdf copied to ./deploy/"
    if [ "$printouts_created" = "true" ]; then
      cp "printout_${document_basename}_A5_on_A4_doublesided_folded.pdf" "./deploy" && echo "  DEPLOY: printout_${document_basename}_A5_on_A4_doublesided_folded.pdf copied to ./deploy/"
      cp "printout_${document_basename}_A5_on_A4_sidebyside_simple.pdf" "./deploy" && echo "  DEPLOY: printout_${document_basename}_A5_on_A4_sidebyside_simple.pdf copied to ./deploy/"
    fi
  else
    echo "  NODEPLOY: resulting files NOT copied to the deploy directory."
  fi

  echo "  SUCCESS: Compilation succesful! Enjoy your ${document_basename}.pdf"

} # END compile_document()


# Test program arguments

deployfinal="true"
createprintouts="true"
partialbooks="true"

while [ $# -gt 0 ]; do
  case "$1" in
    "--no-deploy")
      deployfinal="false"
      shift;;
    "--no-printouts")
      createprintouts="false"
      shift;;
    "--no-partial")
      partialbooks="false"
      shift;;
    "-d")
      deployfinal="false"
      createprintouts="false"
      partialbooks="false"
      shift;;
    *)
      print_usage_and_exit
      ;;
  esac
done


# Test executable availability:
which "pdflatex" >"/dev/null" || die 1 "pdflatex binary not found in path! Aborted."
which "texlua" >"/dev/null" || die 1 "texlua binary not found in path! Aborted."
which "lilypond-book" >"/dev/null" || die 1 "lilypond-book binary not found in path! Aborted."

# Create the 1st level temporary directory in case it doesn't exist.
mkdir "$TEMP_DIRNAME" 2>"/dev/null"
[ -d "./$TEMP_DIRNAME" ] || die 1 "Could not create temporary directory $TEMP_DIRNAME. Aborted."


# Compile the documents (defined at the top of this file):
compile_document "${MAIN_FILENAME_BASE}"
[ ${partialbooks} = "true" ] && compile_document "${PART1_FILENAME_BASE}"
[ ${partialbooks} = "true" ] && compile_document "${PART2_FILENAME_BASE}"

echo ""

# TODO: compile documents simultaneously, but make outputs appear in order

exit 0
