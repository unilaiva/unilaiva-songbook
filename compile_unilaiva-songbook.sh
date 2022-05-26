#!/bin/bash
#
# This bash shell script for UNIX compiles unilaiva-songbook.tex using
# different tools to produce the main output file unilaiva-songbook.pdf
# and others.
#
# Note that this script probably works only with bash, as it uses some of it's
# features, especially arrays.
#
# Usage: run without argument for default operation. Run with --help argument
# for further information about options, or see function print_usage_and_exit
# below.
#
# Required binaries in PATH: lilypond-book, pdflatex, texlua, awk
# Optional binary in PATH: context (will be used to create printout versions)
#


MAIN_FILENAME_BASE="unilaiva-songbook" # filename base for the main document (without .tex suffix)
PART1_FILENAME_BASE="unilaiva-songbook_part1" # filename base for the 2-part document's part 1 (without .tex suffix)
PART2_FILENAME_BASE="unilaiva-songbook_part2" # filename base for the 2-part document's part 2 (without .tex suffix)
ASTRAL_FNAME_PREFIX="unilaiva-astral-" # filename prefix for unilaiva astral books
SELECTION_FNAME_PREFIX="ul-selection" # filename prefix for selections
TEMP_DIRNAME="temp" # just the name of a subdirectory, not an absolute path
SONG_IDX_SCRIPT="ext_packages/songs/songidx.lua"
# The following is the locale used in creating the indexes, thus affecting the
# sort order. Finnish (UTF8) is the default. Note that the locale used must be
# installed on the system. To list installed locales on an UNIX, execute
# "locale -a".
SORT_LOCALE="fi_FI.utf8" # Recommended default: fi_FI.utf8

INITIAL_DIR="${PWD}" # Store the initial directory

ERROR_OCCURRED_FILE="${INITIAL_DIR}/${TEMP_DIRNAME}/compilation_error_occurred"
TOO_MANY_WARNINGS_FILE="${INITIAL_DIR}/${TEMP_DIRNAME}/too_many_warnings"
RESULT_PDF_LIST_FILE="${INITIAL_DIR}/${TEMP_DIRNAME}/result_pdf_list"

# Function: print the program usage informationand exit.
print_usage_and_exit() {
  echo ""
  echo "Usage: compile_unilaiva-songbook.sh [OPTION]... [FILE]..."
  echo ""
  echo "TL;DR: just run without arguments for default operation."
  echo ""
  echo "If run without any arguments, all main .tex documents of Unilaiva songbook"
  echo "(main book, partial booklets and selections) will be compiled with printouts"
  echo "for all of them, and the resulting files will be copied to the 'deploy'"
  echo "directory (if it exists)."
  echo ""
  echo "If file names are given as arguments, only they will be compiled. The files"
  echo "must reside in the project's root directory and have .tex extension."
  echo ""
  echo "Options:"
  echo ""
  echo "  --no-docker     : do not use the Docker container for compiling"
  echo "  --help          : print this usage information"
  echo "  --no-astral     : do not compile unilaiva-astral* books"
  echo "  --no-deploy     : do not copy PDF files to ./deploy/"
  echo "  --no-partial    : do not compile partial books"
  echo "  --no-printouts  : do not create extra printout PDFs"
  echo "  --no-selections : do not create selection booklets"
  echo "  --pull          : Execute git pull before compiling"
  echo "  --sequential    : compile documents sequentially (the default is to"
  echo "                    compile them in parallel)"
  echo "  -q              : use for quick development build of the main document;"
  echo "                    equals to --no-partial --no-selections --no-astral"
  echo "                    --no-printouts --no-deploy"
  echo ""
  echo "In addition to the full songbook, also two-booklet version is created,"
  echo "with parts 1 and 2 in separate PDFs. This is not done, if --no-partial"
  echo "option is present or files are given as arguments."
  echo ""
  echo "'Unilaiva no Astral' books are also compiled by default in addition to"
  echo "Unilaiva Songbook, unless --no-astral option is present or files are"
  echo "given as arguments. 'Unilaiva no Astral' books' main files are named"
  echo "unilaiva-astral-*.tex"
  echo ""
  echo "Also selection booklets, with specific songs only, specified in files"
  echo "named ul-selection_*.pdf are compiled, unless --no-selections option"
  echo "is present or files are given as arguments."
  echo ""
  echo "Special versions for printing (printout_*.pdf) are created for all compiled"
  echo "documents, if 'context' binary is available and --no-printouts option is not"
  echo "given."
  echo ""
  echo "If --no-deploy argument is not present, the resulting PDF files will"
  echo "also be copied to ./deploy/ directory (if it exists)."
  echo ""
  exit 1
}

# Function: exit the program with error code and message.
# Usage: die <errorcode> <message>
die() {
  # Only print errors, if file ${ERROR_OCCURRED_FILE} does NOT exist.
  # If it exists, it means that error processing is already underway,
  # and this is only a child process that has been killed.
  if [ ! -f "${ERROR_OCCURRED_FILE}" ]; then
    # Create the file signifying (for child processes) that we are already
    # dying:
    echo "Error occurred while compiling: $2 (code: $1)" >"${ERROR_OCCURRED_FILE}"
    echo ""
    # Echo the actual error:
    echo "ERROR:   $2" >&2
    cd "${INITIAL_DIR}"
    pkill_available="false"
    which "pkill" >"/dev/null" && pkill_available="true"
    for pid in "${pids[@]}"; do # Loop through the main sub processes
      # If we have 'pkill', kill children of the main sub process first:
      if [ "${pkill_available}" = "true" ]; then
        [ ${pid} != 0 ] && pkill --parent ${pid} -9 >/dev/null 2>&1
      fi
      # Kill the main sub process:
      [ ${pid} != 0 ] && kill -9 ${pid} >/dev/null 2>&1
    done
  fi
  exit $1
}

# Build, create and stat docker container and start the compile script therein.
# Usage: compile_in_docker <arguments for compile script>
compile_in_docker() {

  echo ""

  which "docker" >"/dev/null"
  if [ $? -ne 0 ]; then
    echo "Docker executable not found. Please install Docker to compile the"
    echo "songbook in the 'official' environment. To compile without Docker,"
    echo "use the --no-docker option, but be aware that the resulting book"
    echo "might not be exactly as intended."
    die 1 "Docker executable not found. Aborted."
  fi

  # Build the compiler Docker image only if it doesn't yet exist, or if the
  # Dockerfile (modification date) is newer than the image

  echo "DOCKER   Query compiler image status..."
  docker_build_needed=""
  if [ ! -z $(docker image ls -q unilaiva-compiler) ]; then
    # image exists, compare dates...
    dockerimage_ts="$(date -d $(docker inspect -f '{{ .Created }}' unilaiva-compiler) +%s)"
    dockerfile_ts="$(date -r docker/unilaiva-compiler/Dockerfile +%s)"
    [ ${dockerfile_ts} -gt ${dockerimage_ts} ] && docker_build_needed="true"
  else
    docker_build_needed="true"
  fi

  if [ "${docker_build_needed}" = "true" ]; then
    echo "DOCKER   Build compiler image..."
    # Build the compiler image
    docker build -t unilaiva-compiler ./docker/unilaiva-compiler || die 1 "Docker build error"
    echo "DOCKER   Building image complete."
    echo ""
    echo "         To remove old dangling images and unused volumes, it is safe"
    echo "         to run the following command:"
    echo ""
    echo "           'docker image prune ; docker volume prune'"
    echo ""
    echo "         To remove old images, which are not needed anymore, you have"
    echo "         to find them with 'docker image ls -a' and then remove them"
    echo "         manually with 'docker image rm <image_id>'."
    echo ""
  fi

  echo "DOCKER   Start compiler container..."

  # Run the container with current user's ID and bind mount current directory
  docker run -it --rm \
    --user $(id -u):$(id -g) \
    --mount type=bind,src="$(realpath .)",dst="/unilaiva-songbook" \
    unilaiva-compiler \
    $@
  return $?
}

# Function: compile the document given as parameter
# Usage: compile_document <filename_base_for_tex_document> # without path and without ".tex" suffix
compile_document() {

  # Usage: die_log <errorcode> <message> <logfile>
  die_log() {
    # Only print errors, if file ${ERROR_OCCURRED_FILE} does NOT exist.
    # If it exists, it means that error processing is already underway,
    # and this is only a child process that has been killed.
    if [ ! -f "${ERROR_OCCURRED_FILE}" ]; then
      echo "ERROR    [${document_basename}]: $2"
      echo ""
      echo "Displaying log file for ${document_basename}.tex: $3"
      echo ""
      cat "$3"
      echo ""
      echo "Build logs are in: ${temp_dirname_twolevels}/"
      # Parse output logs for giving better advice:
      if [ "$3" = "out-3_titleidx.log" ]; then # test for locale problem
        grep "invalid locale" "$3" 
        if [ $? -eq 0 ]; then
          echo ""
          echo "Locale ${SORT_LOCALE} must be installed on the system or the compile script"
          echo "must be modified (line starting with SORT_LOCALE) to use a different locale."
        fi
      fi
    fi
    die $1 "[${document_basename}]: $2"
  }

  document_basename="$1"
  temp_dirname_twolevels="${TEMP_DIRNAME}/${document_basename}"

  # Test if we are currently in the correct directory:
  [ -f "./${document_basename}.tex" ] || die 1 "Not currently in the project's root directory! Aborted."

  # Clean old build:
  [ -d "${temp_dirname_twolevels}" ] && rm -R "${temp_dirname_twolevels}"/* 2>"/dev/null"
  # Ensure the build directory exists:
  mkdir -p "${temp_dirname_twolevels}" 2>"/dev/null"
  [ -d "${temp_dirname_twolevels}" ] || die $? "Could not create the build directory ${temp_dirname_twolevels}. Aborted."

  echo "EXEC     [${document_basename}]: lilypond (lilypond-book)"

  # Run lilypond-book. It compiles images out of lilypond source code within tex files and outputs
  # the modified .tex files and the musical staff images created by it to subdirectory ${temp_dirname_twolevels}.
  # The directory (last level only) is created if it doesn't exist.
  lilypond-book -f latex --output="${temp_dirname_twolevels}" "${document_basename}.tex" 1>"${temp_dirname_twolevels}/out-1_lilypond.log" 2>&1 || die_log $? "Error running lilypond-book! Aborted." "${temp_dirname_twolevels}/out-1_lilypond.log"

  # Clean up temporary files from the project root
  # (for some reason they're not written to output dir):
  rm tmp????????.sxc tmp????????.out idx_*.sxd missfont.log 2>"/dev/null"

  # Enter the temp directory. (Do rest of the steps there.)
  cd "${temp_dirname_twolevels}" || die 1 "Cannot enter temporary directory! Aborted."

  # Copy the required files not copied by lilypond to the temp directory:
  mkdir -p "ext_packages/songs" 2>"/dev/null"
  cp "../../tex/unilaiva-songbook_common.sty" "./tex/"
  cp "../../ext_packages/songs/"{songs.sty,songidx.lua} "./ext_packages/songs/"
  cp "../../tags.can" "./"
  ln -s "../../../content/img" "./content/" 2>"/dev/null"  # images are big, so link instead of copy

  echo "EXEC     [${document_basename}]: pdflatex (1st run)"

  # First run of pdflatex:
  pdflatex -draftmode -file-line-error -interaction=nonstopmode "${document_basename}.tex" 1>"out-2_pdflatex.log" 2>&1 || die_log $? "Compilation error running pdflatex! Aborted." "out-2_pdflatex.log"

  # Only create indices, if not compiling a selection booklet (bashism):
  if [[ ${document_basename} != ${SELECTION_FNAME_PREFIX}* ]]; then
    echo "EXEC     [${document_basename}]: texlua (create indices)"

    # Create indices:
    texlua "${SONG_IDX_SCRIPT}" -l ${SORT_LOCALE} "idx_${document_basename}_title.sxd" "idx_${document_basename}_title.sbx" 1>"out-3_titleidx.log" 2>&1 || die_log $? "Error creating song title indices! Aborted." "out-3_titleidx.log"
    # Author index creation is commented out, as it is not used (now):
    # texlua "${SONG_IDX_SCRIPT}" -l ${SORT_LOCALE} idx_${document_basename}_auth.sxd idx_${document_basename}_auth.sbx 1>"out-4_authidx.log" 2>&1 || die_log $? "Error creating author indices! Aborted." "out-4_authidx.log"
    texlua "${SONG_IDX_SCRIPT}" -l ${SORT_LOCALE} -b "tags.can" "idx_${document_basename}_tag.sxd" "idx_${document_basename}_tag.sbx" 1>"out-5_tagidx.log" 2>&1 || die_log $? "Error creating tag (scripture) indices! Aborted." "out-5_tagidx.log"
  fi

  echo "EXEC     [${document_basename}]: pdflatex (2nd run)"

  # Second run of pdflatex:
  pdflatex -draftmode -file-line-error -interaction=nonstopmode "${document_basename}.tex" 1>"out-6_pdflatex.log" 2>&1 || die_log $? "Compilation error running pdflatex (2nd time)! Aborted." "out-6_pdflatex.log"

  echo "EXEC     [${document_basename}]: pdflatex (3rd run)"

  # Third run of pdflatex, creates the final main PDF document:
  pdflatex -file-line-error -interaction=nonstopmode "${document_basename}.tex" 1>"out-7_pdflatex.log" 2>&1 || die_log $? "Compilation error running pdflatex (3rd time)! Aborted." "out-7_pdflatex.log"

  cp "${document_basename}.pdf" "../../" || die $? "Error copying ${document_basename}.pdf from temporary directory! Aborted."
  echo "${document_basename}.pdf" >>${RESULT_PDF_LIST_FILE}

  # Check warnings in the logs

  lp_barwarning_count=$(grep -i "warning: barcheck" "out-1_lilypond.log" | wc -l)
  overfull_count=$(grep -i overfull "out-7_pdflatex.log" | wc -l)
  underfull_count=$(grep -i underfull "out-7_pdflatex.log" | wc -l)
  fontwarning_count=$(grep -i "Font Warning" "out-7_pdflatex.log" | wc -l)
  [ "${lp_barwarning_count}" -gt "0" ] && echo "DEBUG    [${document_basename}]: Lilypond bar check warnings: ${lp_barwarning_count}"
  [ "${overfull_count}" -gt "0" ] && echo "DEBUG    [${document_basename}]: Overfull warnings: ${overfull_count}"
  [ "${underfull_count}" -gt "0" ] && echo "DEBUG    [${document_basename}]: Underfull warnings: ${underfull_count}"
  if [ "${fontwarning_count}" -gt "20" ]; then
    echo "DEBUG    [${document_basename}]: Font warnings: ${fontwarning_count}; CHECK THE LOG!!"
    echo "Too many Font warnings! There is a problem!" >>"${TOO_MANY_WARNINGS_FILE}"
  else
    [ "${fontwarning_count}" -gt "0" ] && echo "DEBUG    [${document_basename}]: Font warnings: ${fontwarning_count}"
  fi

  # Create printouts, if filename contains _A5 and printouts are not disabled
  # by a command line argument:

  if [[ "${document_basename}" != *"_A5"* ]]; then
    echo "NOEXEC   [${document_basename}]: Extra printout PDFs not created, no _A5 in filename"
  else
    if [ ${createprintouts} != "true" ]; then
      echo "NOEXEC   [${document_basename}]: Extra printout PDFs not created as per request"
    else
      which "context" >"/dev/null"
      if [ $? -ne 0 ]; then
        echo "NOEXEC   [${document_basename}]: Extra printout PDFs not created; no 'context'"
      else
        echo "EXEC     [${document_basename}]: context (create printouts)"

        # A5 on A4, double sided, folded: Use 'awk' to create a copy of the
        # printout template file with changed input PDF file name and then
        # execute 'context' on the new file.
        printout_dsf_basename="printout_${document_basename}_on_A4_doublesided_folded"
        awk "/unilaiva-songbook.pdf/"' { gsub( "'"unilaiva-songbook.pdf"'", "'"${document_basename}.pdf"'" ); t=1 } 1; END{ exit( !t )}' "../../tex/printout_template_A5_on_A4_doublesided_folded.context" >"${printout_dsf_basename}.context" || die $? "[${document_basename}]: Error with 'awk' when creating dsf printout! Aborted."
        context "${printout_dsf_basename}.context" 1>"out-8_printout-dsf.log" 2>&1 || die_log $? "Error creating dsf printout! Aborted." "out-8_printout-dsf.log"
        cp "${printout_dsf_basename}.pdf" "../../" || die $? "Error copying printout PDF from temporary directory! Aborted."
        echo "${printout_dsf_basename}.pdf" >>${RESULT_PDF_LIST_FILE}

        # A5 on A4, a A5-A5 spread on single A4 surface: Use 'awk' to create a
        # copy of the printout template file with changed input PDF file name
        # and then execute 'context' on the new file.
        printout_sss_basename="printout_${document_basename}_on_A4_sidebyside_simple"
        awk "/unilaiva-songbook.pdf/"' { gsub( "'"unilaiva-songbook.pdf"'", "'"${document_basename}.pdf"'" ); t=1 } 1; END{ exit( !t )}' "../../tex/printout_template_A5_on_A4_sidebyside_simple.context" >"${printout_sss_basename}.context" || die $? "[${document_basename}]: Error with 'awk' when creating sss printout! Aborted."
        context "${printout_sss_basename}.context" 1>"out-9_printout-sss.log" 2>&1 || die_log $? "Error creating sss printout! Aborted." "out-9_printout-sss.log"
        cp "${printout_sss_basename}.pdf" "../../" || die $? "Error copying printout PDF from temporary directory! Aborted."
        echo "${printout_sss_basename}.pdf" >>${RESULT_PDF_LIST_FILE}
      fi
    fi
  fi

  # Clean up the compile directory: remove some temporary files.
  rm tmp*.out tmp*.sxc 2>"/dev/null"

  # Get out of ${temp_dirname_twolevels}:
  cd "${INITIAL_DIR}" || die $? "Cannot return to the main directory."

  echo "DEBUG    [${document_basename}]: Build logs in ${temp_dirname_twolevels}/"
  echo "SUCCESS  [${document_basename}.pdf]: Compilation successful!"

} # END compile_document()

# Copies the result .pdf's to the deploy directory, if:
#   - not inside Docker container
#   - deploy is not forbidden by command line argument
#   - deploy directory exists
deploy_results() {
  [ -z "${IN_UNILAIVA_DOCKER_CONTAINER}" ] || return
  [ "${deployfinal}" = "true" ] || return
  if [ ! -d "./deploy" ]; then
    echo "NODEPLOY Resulting PDF files NOT copied to ./deploy/ (directory not found)"
    return
  fi
  while IFS= read -r pdf_file; do
    [ -f "${pdf_file}" ] || die 21 "Could not access ${pdf_file} for deployment"
    cp "${pdf_file}" "./deploy/"
    [ $? -eq 0 ] || die 22 "Could not deploy ${pdf_file}"
    echo "DEPLOY   ${pdf_file} copied to ./deploy/"
  done < "${RESULT_PDF_LIST_FILE}"
} # END deploy_results()

# Set defaults:
usedocker="true"
deployfinal="true"
createprintouts="true"
mainbook="true"
astralbooks="true"
partialbooks="true"
selections="true"
gitpull="false"
parallel="true"

doc_count=0 # will be increased when documents are added to 'docs' array

all_args="$@"

# Remove the file that's existence signifies that the last compilation had
# errors. Do it already here to ensure correct working of die() function.
if [ -f ${ERROR_OCCURRED_FILE} ]; then
  rm "${ERROR_OCCURRED_FILE}" >"/dev/null" 2>&1
fi

# Test program arguments:
while [ $# -gt 0 ]; do
  case "$1" in
    "--no-docker")
      usedocker="false"
      shift;;
    "--no-deploy")
      deployfinal="false"
      shift;;
    "--no-partial")
      partialbooks="false"
      shift;;
    "--no-printouts")
      createprintouts="false"
      shift;;
    "--no-selections")
      selections="false"
      shift;;
    "--no-astral")
      astralbooks="false"
      shift;;
    "--pull")
      gitpull="true"
      shift;;
    "--sequential")
      parallel="false"
      shift;;
    "-q")
      deployfinal="false"
      createprintouts="false"
      astralbooks="false"
      partialbooks="false"
      selections="false"
      shift;;
    "--help")
      print_usage_and_exit
      ;;
    *) # for everything else (possibly a file name)
      if [ -f "$1" ]; then
        tmp=$1
        tmp=${tmp##*/} # remove everything before and including the last /
        case "${tmp}" in
          *.tex) ;; # is a .tex file, good
          *) die 1 "Given file does not have a .tex extension! Aborted."
        esac
        [ -f "${tmp}" ] || die 1 "Given file is not in the current directory! Aborted."
        tmp=${tmp%.tex} # remove the suffix
        docs[doc_count]=${tmp} ; ((doc_count++))
        # Compile only the given file, when files are explicitly given:
        mainbook="false"
        astralbooks="false"
        partialbooks="false"
        selections="false"
      else
        echo ""
        echo "ERROR:   Incorrect argument or nonexisting file name."
        print_usage_and_exit
      fi
      shift;;
  esac
done

[ -f "./compile_unilaiva-songbook.sh" ] || die 1 "Not currently in the project's root directory! Aborted."

if [ -z "${IN_UNILAIVA_DOCKER_CONTAINER}" ]; then # not in container (yet)
  if [ ${usedocker} = "true" ]; then
    compile_in_docker ${all_args}
    retcode=$?
    [ ${retcode} -eq 0 ] || exit ${retcode}
    deploy_results
    echo ""
    echo "Done."
    echo ""
    exit 0
  fi
fi

# Test executable availability:
which "pdflatex" >"/dev/null" || die 1 "'pdflatex' binary not found in path! Aborted."
which "texlua" >"/dev/null" || die 1 "'texlua' binary not found in path! Aborted."
which "lilypond-book" >"/dev/null" || die 1 "'lilypond-book' binary not found in path! Aborted."
which "awk" >"/dev/null" || die 1 "'awk' binary not found in path! Aborted."

if [ ${gitpull} = "true" ]; then
  which "git" >"/dev/null" || die 1 "'git' binary not found in path! Aborted."
  git pull --rebase
  [ $? -eq 0 ] || die 5 "Cannot pull changes from git as requested. Aborted."
fi

# Create the 1st level temporary directory in case it doesn't exist.
mkdir "${TEMP_DIRNAME}" 2>"/dev/null"
[ -d "./${TEMP_DIRNAME}" ] || die 1 "Could not create temporary directory ${TEMP_DIRNAME}. Aborted."

# Remove the files signifying the last compilation had problems,
# if they exist (${ERROR_OCCURRED_FILE} has been removed earlier):
rm "${TOO_MANY_WARNINGS_FILE}" >"/dev/null" 2>&1
rm "${RESULT_PDF_LIST_FILE}" >"/dev/null" 2>&1

trap 'die 130 Interrupted.' INT TERM # trap interruptions

# Insert the documents to be compiled to 'docs' array

if [ ${mainbook} = "true" ]; then
  docs[doc_count]="${MAIN_FILENAME_BASE}" ; ((doc_count++))
fi
if [ ${partialbooks} = "true" ]; then  # add partial books
  docs[doc_count]="${PART1_FILENAME_BASE}" ; ((doc_count++))
  docs[doc_count]="${PART2_FILENAME_BASE}" ; ((doc_count++))
fi
if [ ${astralbooks} = "true" ]; then
  i=0
  for f in ${ASTRAL_FNAME_PREFIX}*.tex
  do
    if [ -f "${f}" ]; then  # if normal file
      docs[doc_count]="${f%.tex}" ; ((doc_count++))
    fi
  done
fi
if [ ${selections} = "true" ]; then  # add selecion booklets
  i=0
  for f in ${SELECTION_FNAME_PREFIX}*.tex
  do
    if [ -f "${f}" ]; then  # if normal file
      docs[doc_count]="${f%.tex}" ; ((doc_count++))
    fi
  done
fi

dockerized_text=""
[ -z ${IN_UNILAIVA_DOCKER_CONTAINER} ] || dockerized_text=" within docker container"
echo ""
if [ ${doc_count} = 1 ]; then
  echo "Compiling Unilaiva songbook (1 document${dockerized_text})..."
else
  parallel_text="sequentially"
  [ ${parallel} = "true" ] && parallel_text="in parallel"
  echo "Compiling Unilaiva songbook (${doc_count} documents ${parallel_text}${dockerized_text})..."
fi
echo ""

# Compile the documents in the 'docs' array:
pid_count=0
pids[0]=0  # 'pids' array will contain PIDs of sub processes
for doc in "${docs[@]}"; do
  compile_document "${doc}" &
  pids[pid_count]=$!
  if [ ${parallel} = "true" ]; then
    ((pid_count++))
  else
    wait  # wait for the last compile_document to finish
    pids[pid_count]=0  # reset PID
  fi
done

wait # wait for all sub processes to end

deploy_results

if [ -e "${TOO_MANY_WARNINGS_FILE}" ]; then
  echo ""
  echo "!!! WARNING !!!"
  echo ""
  echo "There were too many font warnings. Probably the fonts in the result"
  echo "document(s) are not as they should be."
  if [ "${usedocker}" = "false" ]; then
    echo ""
    echo "Please run the script without --no-docker option to compile the"
    echo "songbook within a fully working environment to ensure perfect"
    echo "results. For that, Docker installation is required. See README.md"
  fi
fi

if [ -z ${IN_UNILAIVA_DOCKER_CONTAINER} ]; then
  echo ""
  echo "Done."
  echo ""
else
  echo "DOCKER   Stop compiler container..."
fi

exit 0
