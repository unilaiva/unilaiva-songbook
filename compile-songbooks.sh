#!/bin/bash
#
# This bash shell script for Linux compiles songbooks, in the Unilaiva songbook
# family of books, using different tools to produce the main output file
# unilaiva-songbook_A5.pdf and others.
#
# Note that this script -- unmodified -- probably works only with bash, as it
# uses some of it's features, especially for arrays, arithmetic and $BASHPID.
# Bash version 4 or higher is required, and tested for. If using Docker for
# compiling, as is the default, Bash version 3 is enough on the host system.
#
# Required binaries in PATH: bash, lilypond-book, lualatex, texlua, awk, ps
# Optional binaries in PATH:
#   - docker: for default compilation mode inside container
#   - context: used to create printout versions
#
# Usage: run without argument for default operation. Run with --help argument
# for further information about options, or see function print_usage_and_exit
# below.
#


# Set this to 1 if wanting to use colors, 0 otherwise. The terminal's support
# for colors is tested, and if it is missing, the color codes are disabled
# regardless of this setting.
USE_COLORS=1

# Maximum number of parallel compilation jobs. Each job takes quite a bit
# of memory, so this should be limited.
MAX_PARALLEL=6
# Maximum total memory use for Docker container. 5g should be enough for 6
# parallel jobs. This is passed to docker with --memory option.
MAX_DOCKER_MEMORY="5g"
# Maximum total memory and swap (together) use for Docker container. If set
# to same as MAX_DOCKER_MEMORY, swap is disabled. This is passed to docker with
# # --memory-swap option.
MAX_DOCKER_MEMORY_PLUS_SWAP="5g"


MAIN_FILENAME_BASE="unilaiva-songbook_A5" # filename base for the main document (without .tex suffix)
PART1_FILENAME_BASE="unilaiva-songbook_part1_A5" # filename base for the 2-part document's part 1 (without .tex suffix)
PART2_FILENAME_BASE="unilaiva-songbook_part2_A5" # filename base for the 2-part document's part 2 (without .tex suffix)
ASTRAL_FNAME_PREFIX="unilaiva-astral" # filename prefix for unilaiva astral books
SELECTION_FNAME_PREFIX="ul-selection" # filename prefix for selections
TEMP_DIRNAME="temp" # just the name of a subdirectory, not an absolute path
RESULT_DIRNAME="result" # just the name of a subdirectory, not an absolute path
RESULT_AUDIO_DIRNAME="result/audio" # just the name of a subdirectory, not an absolute path
RESULT_MIDI_DIRNAME="result/midi" # just the name of a subdirectory, not an absolute path
DEPLOY_DIRNAME="deploy" # just the name of a subdirectory, not an absolute path
SONG_IDX_SCRIPT="tex/ext_packages/songs/songidx.lua"
# The following is the locale used in creating the indexes, thus affecting the
# sort order. Finnish (UTF8) is the default. Note that the locale used must be
# installed on the system. To list installed locales on an UNIX, execute
# "locale -a".
SORT_LOCALE="fi_FI.utf8" # Recommended default: fi_FI.utf8

INITIAL_DIR="${PWD}" # Store the initial directory

TOO_MANY_WARNINGS_FILE="${INITIAL_DIR}/${TEMP_DIRNAME}/too_many_warnings"
RESULT_PDF_LIST_FILE="${INITIAL_DIR}/${TEMP_DIRNAME}/result_pdf_list"

main_pid=$$
# Function: print the program usage informationand exit.
print_usage_and_exit() {
  echo ""
  echo "Usage: compile-songbooks.sh [OPTION]... [FILE]..."
  echo ""
  echo "TL;DR: just run without arguments for default operation. The resulting"
  echo "       PDF files will be put in the '${RESULT_DIRNAME}' subdirectory."
  echo ""
  echo "If run without any arguments, all main .tex documents of Unilaiva songbook"
  echo "family (main book, astral books, partial booklets and selections) will be"
  echo "compiled, plus all supported extra formats for all of them, and the"
  echo "resulting files will be copied to the '${DEPLOY_DIRNAME}' directory (if it exists)."
  echo ""
  echo "If file names are given as arguments, *only* they will be compiled. The"
  echo "files must reside in the project's root directory and have .tex extension."
  echo ""
  echo "Options:"
  echo ""
  echo "  --help          : print this usage information"
  echo "  --no-audio      : do not create audio (mp3) files from Lilypond sources"
  echo "  --no-astral     : do not compile unilaiva-astral* books"
  echo "  --no-deploy     : do not copy PDF files to ./${DEPLOY_DIRNAME}/"
  echo "  --no-docker     : do not use the Docker container for compiling"
  echo "  --no-lyric      : do not generate additional lyrics-only books"
  echo "  --no-midi       : do not copy MIDI files created by Lilypond to the result"
  echo "                    directory"
  echo "  --no-partial    : do not compile partial books"
  echo "  --no-printouts  : do not create extra printout PDFs"
  echo "  --no-selections : do not create selection booklets"
  echo "  --pull          : Execute git pull before compiling;"
  echo "                    this is always done outside Docker"
  echo "  --sequential    : compile documents sequentially (the default is to"
  echo "                    compile them in parallel), use on low memory systems"
  echo "  --shell         : Execute an interactive shell within docker only,"
  echo "                    does not compile anything."
  echo "  -q              : use for quick development build of the main document;"
  echo "                    equals to --no-partial --no-selections --no-astral"
  echo "                    --no-printouts --no-deploy --no-midi --no-audio"
  echo "                    --no-lyric"
  echo ""
  echo "In addition to the full version of tha main Unilaiva Songbook, also"
  echo "two-booklet version of it is created, with parts 1 and 2 in separate PDFs."
  echo "This is not done, if --no-partial option is present or files are given"
  echo "as arguments."
  echo ""
  echo "'Unilaiva no Astral' books are also compiled by default in addition to"
  echo "Unilaiva Songbook, unless --no-astral option is present or files are"
  echo "given as arguments. 'Unilaiva no Astral' books' main files are named"
  echo "unilaiva-astral-*.tex"
  echo ""
  echo "Also selection booklets, with specific songs only, specified in files"
  echo "named ul-selection_*.tex are compiled, unless --no-selections option"
  echo "is present or files are given as arguments."
  echo ""
  echo "If .tex files are explicitly given on the command line, only those"
  echo "documents are compiled."
  echo ""
  echo "By default, additional lyrics-only books are generated also. They have"
  echo "no notation, chords, etc. musical information, except for lyrics and"
  echo "bar lines. Use --no-lyric option to not create them."
  echo ""
  echo "By default, MIDI files and audio files are extracted and generated from"
  echo "Lilypond sources and copied to '${RESULT_MIDI_DIRNAME}' and '${RESULT_AUDIO_DIRNAME}'"
  echo "respectively, unless --no-midi or --no-audio options are present."
  echo ""
  echo "For documents containing _A5 in their filename, special versions for"
  echo "printing on A4 sized paper are created, if 'context' binary is available"
  echo "and --no-printouts option is not given."
  echo ""
  echo "The resulting PDF files will also be copied to ./${DEPLOY_DIRNAME}/ directory (if"
  echo "it exists), unless they have _NODEPLOY in their filename or --no-deploy"
  echo "option is given."
  echo ""
  exit 1
}

# Function: final clean up needed to run before exiting the whole script
cleanup() {
  # return to the original directory
  cd "${INITIAL_DIR}"
  # Clean up temporary files from the project root, they are sometimes left
  # behind.
  rm tmp????????.sxc tmp????????.out tmp????????.log tmp????????.pdf idx_*.sxd missfont.log 2>"/dev/null"
}

# Function: sends a signal to a tree of processes (default: KILL)
# Usage: killtree <root process> <signal>
#
# The given signal is sent to the root process and all it's children
# recursively, leaf first. Current subshell and the main shell, if included
# in the tree, are not included. If signal argument is omitted, KILL signal
# is used as the default.
#
# The signal is not sent to the current process or the main process even if
# they are in the tree.
#
# Calls binaries 'kill' and 'ps', requires Bash version 4 or higher.
# Note: $$ holds the main shell's PID, and $BASHPID (introduced in Bash v4)
# holds the current subshell's PID.
killtree() {
  local _pid=$1
  local _sig=${2:-KILL}
  # Stops a parent before killing it's children, to prevent it forking new
  # children:
  [ ${_pid} -ne ${BASHPID} ] && [ ${_pid} -ne ${$} ] && kill -STOP ${_pid} >/dev/null 2>&1
  # Recursively handle the children:
  for _child in $(ps -o pid --no-headers --ppid ${_pid}); do
    killtree ${_child} ${_sig}
  done
  # We're at the bottom of the recursion, kill the process, unless it is the
  # main process or the current process:
  if [ ${_pid} -ne ${BASHPID} ] && [ ${_pid} -ne ${$} ]; then
    kill -${_sig} ${_pid} >/dev/null 2>&1
    wait ${_pid} 2>/dev/null # This wait suppresses the "Killed" output
  fi
}

# Function: print error code and message, kill subprocesses and exit the program.
# Usage: die <errorcode> <message>
#
# If this is called from a subprocess, the error is printed, and TERM signal
# sent to the main process, and exit the subprocess. Main process has trapped
# TERM signal, and will respond by calling this function again with <errorcode>
# 99.
#
# If this is called from the main process, print error only if <errorcode> is
# not 99, then kill all the subprocesses, run final cleanup and exit.
#
# Requires Bash v4 or higher for $BASHPID, for current (sub)process id.
die() {
  # Do not print the error, if <errorcode> is 99 and we're in the main process.
  if [ ${1} -eq 99 ] && [ ${$} -eq ${BASHPID} ]; then
    echo -e "${PRETXT_ABORTED}${C_YELLOW}All compilations are aborted.${C_RESET}" >&2
  else
    # Print the error:
    echo -e "${PRETXT_ERROR}${2}" >&2
  fi
  if [ ${$} -eq ${BASHPID} ]; then
    # We're in the main process.
    # Kill the whole tree of child processes:
    killtree ${$} KILL
    # Make the final clean up:
    cleanup
  else
    # We're in a sub process.
    # Send a TERM signal to the main process, it will handle the killing of
    # children and the finalisation of the script.
    kill -TERM ${$}
  fi
  exit $1
}

# Function: set up UI strings and colors, called in the beginning of the script
setup_ui() {
  # Test if colorization is supported
  if [ "$USE_COLORS" -eq 1 ]; then
    if [[ "$TERM" = *xterm*color* ]]; then
      USE_COLORS=1
    elif [ -x /usr/bin/tput ] && tput setaf 1 >&/dev/null; then
      # We have color support; assume it's compliant with Ecma-48
      # (ISO/IEC-6429). (Lack of such support is extremely rare, and such
      # a case would tend to support setf rather than setaf.)
      USE_COLORS=1
    else
      USE_COLORS=0
    fi
  fi
  if [ "$USE_COLORS" -eq 1 ]; then # define colors
    C_BLACK="\033[0;30m" ; C_BLUE="\033[0;34m"     ; C_GREEN="\033[0;32m"
    C_CYAN="\033[0;36m"  ; C_RED="\033[0;31m"      ; C_MAGENTA="\033[0;35m"
    C_BROWN="\033[0;33m" ; C_GRAY="\033[0;37m"     ; C_DGRAY="\033[1;30m"
    C_LBLUE="\033[1;34m" ; C_LGREEN="\033[1;32m"   ; C_LCYAN="\033[1;36m"
    C_LRED="\033[1;31m"  ; C_LMAGENTA="\033[1;35m" ; C_YELLOW="\033[1;33m"
    C_WHITE="\033[1;37m" ; C_RESET="\033[0m"
  else # if colors are not supported, set color strings empty
    C_BLACK="" ; C_BLUE=""     ; C_GREEN=""
    C_CYAN=""  ; C_RED=""      ; C_MAGENTA=""
    C_BROWN="" ; C_GRAY=""     ; C_DGRAY=""
    C_LBLUE="" ; C_LGREEN=""   ; C_LCYAN=""
    C_LRED=""  ; C_LMAGENTA="" ; C_YELLOW=""
    C_WHITE="" ; C_RESET=""
  fi
  # setup DOC_COLORS; each document gets it's own color from this array
  DOC_COLORS[0]="${C_BROWN}"
  DOC_COLORS[1]="${C_MAGENTA}"
  DOC_COLORS[2]="${C_CYAN}"
  DOC_COLORS[3]="${C_BLUE}"
  DOC_COLORS[4]="${C_YELLOW}"
  DOC_COLORS[5]="${C_LMAGENTA}"
  DOC_COLORS[6]="${C_LCYAN}"
  DOC_COLORS[7]="${C_LBLUE}"
  DOC_COLOR_COUNT=8
  # Some UI Text
  PRETXT_DOCKER="${C_WHITE}DOCKER   ${C_RESET}"
  PRETXT_GIT="${C_WHITE}GIT      ${C_RESET}"
  PRETXT_START="${C_GREEN}START    ${C_RESET}"
  PRETXT_EXEC="${C_WHITE}EXEC     ${C_RESET}"
  PRETXT_NOEXEC="${C_DGRAY}NOEXEC   ${C_RESET}"
  PRETXT_DEPLOY="${C_WHITE}DEPLOY   ${C_RESET}"
  PRETXT_NODEPLOY="${C_DGRAY}NODEPLOY ${C_RESET}"
  PRETXT_DEBUG="${C_DGRAY}DEBUG    ${C_RESET}"
  PRETXT_SUCCESS="${C_LGREEN}SUCCESS  ${C_RESET}"
  PRETXT_ERROR="${C_RED}ERROR    ${C_RESET}"
  PRETXT_ABORTED="${C_RED}ABORTED  ${C_RESET}"
  PRETXT_SEE="See:     "
  PRETXT_SPACE="         "
  TXT_DONE="${C_GREEN}Done.${C_RESET}"
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
    die 1 "Docker executable not found."
  fi

  # Build the compiler Docker image only if it doesn't yet exist, or if the
  # Dockerfile (modification date) is newer than the image

  echo -e "${PRETXT_DOCKER}Query compiler image status"
  docker_build_needed=""
  if [ ! -z $(docker image ls -q unilaiva-compiler) ]; then
    # image exists, compare dates...
    # NOTE: Date comparison does not work with date -d on MacOS.
    dockerimage_ts="$(date -d $(docker inspect -f '{{ .Created }}' unilaiva-compiler) +%s)"
    if [ $? -eq 0 ]; then
      # first date command worked, do the rest of the comparison
      dockerfile_ts="$(date -r docker/unilaiva-compiler/Dockerfile +%s)"
      [ ${dockerfile_ts} -gt ${dockerimage_ts} ] && docker_build_needed="true"
    else
     echo -e "${PRETXT_ERROR}Can not test the version of docker image. Rebuild manually if needed."
    fi
  else
    docker_build_needed="true"
  fi

  if [ "${docker_build_needed}" = "true" ]; then
    echo -e "${PRETXT_DOCKER}Build compiler image..."
    # Build the compiler image
    docker build -t unilaiva-compiler ./docker/unilaiva-compiler || die 1 "Docker build error"
    echo -e "${PRETXT_DOCKER}Building image complete."
    echo ""
    echo -e "${PRETXT_SPACE}To remove old dangling images and unused volumes, it is safe"
    echo -e "${PRETXT_SPACE}to run the following command:"
    echo ""
    echo -e "${PRETXT_SPACE}'docker image prune ; docker volume prune'"
    echo ""
    echo -e "${PRETXT_SPACE}To remove old images, which are not needed anymore, you have"
    echo -e "${PRETXT_SPACE}to find them with 'docker image ls -a' and then remove them"
    echo -e "${PRETXT_SPACE}manually with 'docker image rm <image_id>'."
    echo ""
  fi

  echo -e "${PRETXT_DOCKER}Start compiler container"

  # Run the container with current user's ID and bind mount current directory
  docker run -it --rm --read-only \
    --memory="${MAX_DOCKER_MEMORY}" \
    --memory-swap="${MAX_DOCKER_MEMORY_PLUS_SWAP}" \
    --user $(id -u):$(id -g) \
    --mount type=bind,src="$(realpath .)",dst="/unilaiva-songbook" \
    --mount type=volume,src="unilaiva-compiler_homecache",dst="/home/unilaiva" \
    --mount type=tmpfs,tmpfs-size=128m,dst="/tmp" \
    --mount type=tmpfs,tmpfs-size=16m,dst="/run" \
    unilaiva-compiler \
    $@
  return $?
}


# Function: compile the document given as parameter
# Usage: compile_document <filename_base_for_tex_document> <doc_color_string>
#        - Give filename without path and without ".tex" suffix.
#        - doc_color_string is a string containing escaped color instructions
#        - Intended to be called with & to start a new subprocess
compile_document() {

  # Function: prints the error log and calls die().
  # Usage: die_log <errorcode> <message> <logfile>
  die_log() {
    echo -e "${PRETXT_ERROR}${txt_docbase}: ${2}"
    echo ""
    echo -e "${C_WHITE}Displaying log file for ${txt_doctex}: ${C_YELLOW}${3}${C_RESET}"
    echo ""
    cat "${3}"
    echo ""
    echo -e "${PRETXT_SEE}${C_YELLOW}${temp_dirname_twolevels}/${3}${C_RESET}"
    echo ""
    # Parse output logs for giving better advice:
    if [ "${3}" = "log-03_titleidx.log" ]; then # test for locale problem
      grep "invalid locale" "${3}"
      if [ ${?} -eq 0 ]; then
        echo ""
        echo -e "${C_RED}Locale ${SORT_LOCALE} must be installed on the system or the compile script"
        echo -e "must be modified (line starting with SORT_LOCALE) to use a different locale.${C_RESET}"
      fi
    fi
    die $1 "${txt_docbase}: $2\n${PRETXT_SPACE}Exit code: ${C_RED}${1}1${C_RESET}"
  }

  # Function: compile the document given as parameter.
  # Only creates a PDF document. Must already be in the subdirectory created by
  # lilypond-book. Available for compile_document only.
  # Usage: compile_document <filename_base_for_tex_document> <doc_color_string>
  #        - Give filename without path and without ".tex" suffix.
  #        - doc_color_string is a string containing escaped color instructions
  #        - prefix for log filenames, can be empty string
  compile_document_sub() {

    local currentdoc_basename="${1}"
    local txt_docbase="${C_DGRAY}[${2}${1}${C_DGRAY}]${C_RESET}"
    local logfileprefix="${3}"

    echo -e "${PRETXT_EXEC}${txt_docbase}: lualatex (1st run)"

    # First run of lualatex:
    local log02file="${logfileprefix}log-02_lualatex.log"
    lualatex -draftmode -file-line-error -halt-on-error -interaction=nonstopmode "${currentdoc_basename}.tex" 1>"${log02file}" 2>&1 || die_log $? "Compilation error running lualatex!" "${log02file}"

    # Only create indices, if not compiling a selection booklet (bashism):
    if [[ ${currentdoc_basename} != ${SELECTION_FNAME_PREFIX}* ]]; then
      echo -e "${PRETXT_EXEC}${txt_docbase}: texlua (create indices)"

      # Create indices:
      local log03file="${logfileprefix}log-03_titleidx.log"
      texlua "${SONG_IDX_SCRIPT}" -l ${SORT_LOCALE} "idx_title.sxd" "idx_title.sbx" 1>"${log03file}" 2>&1 || die_log $? "Error creating song title indices!" "${log03file}"
      # Author index creation is commented out, as it is not used (now):
      # local log04file="${logfileprefix}log-04_authidx.log"
      # texlua "${SONG_IDX_SCRIPT}" -l ${SORT_LOCALE} idx_auth.sxd idx_auth.sbx 1>"${log04file}" 2>&1 || die_log $? "Error creating author indices!" "${log04file}"
      local log05file="${logfileprefix}log-05_tagidx.log"
      texlua "${SONG_IDX_SCRIPT}" -l ${SORT_LOCALE} -b "tags.can" "idx_tag.sxd" "idx_tag.sbx" 1>"${log05file}" 2>&1 || die_log $? "Error creating tag (scripture) indices!" "${log05file}"
    fi

    echo -e "${PRETXT_EXEC}${txt_docbase}: lualatex (2nd run)"

    # Second run of lualatex:
    local log06file="${logfileprefix}log-06_lualatex.log"
    lualatex -draftmode -file-line-error -halt-on-error -interaction=nonstopmode "${currentdoc_basename}.tex" 1>"${log06file}" 2>&1 || die_log $? "Compilation error running lualatex (2nd time)!" "${log06file}"

    echo -e "${PRETXT_EXEC}${txt_docbase}: lualatex (3rd run)"

    # Third run of lualatex, creates the final main PDF document:
    local log07file="${logfileprefix}log-07_lualatex.log"
    lualatex -file-line-error -halt-on-error -interaction=nonstopmode "${currentdoc_basename}.tex" 1>"${log07file}" 2>&1 || die_log $? "Compilation error running lualatex (3rd time)!" "${log07file}"

    cp "${currentdoc_basename}.pdf" "../../${RESULT_DIRNAME}/" || die $? "Error copying ${currentdoc_basename}.pdf from temporary directory!"
    echo "${currentdoc_basename}.pdf" >>${RESULT_PDF_LIST_FILE}

    # Create printouts, if filename contains _A5 and printouts are not disabled
    # by a command line argument:

    if [[ "${currentdoc_basename}" != *"_A5"* ]]; then
      echo -e "${PRETXT_NOEXEC}${txt_docbase}: Extra printout PDFs not created, no _A5 in filename"
    else
      if [ ${createprintouts} != "true" ]; then
        echo -e "${PRETXT_NOEXEC}${txt_docbase}: Extra printout PDFs not created as per request"
      else
        which "context" >"/dev/null"
        if [ $? -ne 0 ]; then
          echo -e "${PRETXT_NOEXEC}${txt_docbase}: Extra printout PDFs not created; no 'context'"
        else
          echo -e "${PRETXT_EXEC}${txt_docbase}: context (create printouts)"

          # A5 on A4, double sided, must cut: Use 'awk' to create a copy of the
          # printout template file with changed input PDF file name and then
          # execute 'context' on the new file.
          printout_dsf_basename="printout-BOOKLET_${currentdoc_basename}-on-A4-doublesided-needs-cutting"
          awk "/replace-this-filename.pdf/"' { gsub( "'"replace-this-filename.pdf"'", "'"${currentdoc_basename}.pdf"'" ); t=1 } 1; END{ exit( !t )}' "../../tex/printout-template_BOOKLET-A5-on-A4-doublesided-needs-cutting.context" >"${printout_dsf_basename}.context" || die $? "[${currentdoc_basename}]: Error with 'awk' when creating dsf printout!"
          local log08file="${logfileprefix}log-08_printout-dsf.log"
          context "${printout_dsf_basename}.context" 1>"${log08file}" 2>&1 || die_log $? "Error creating dsf printout!" "${log08file}"
          cp "${printout_dsf_basename}.pdf" "../../${RESULT_DIRNAME}/" || die $? "Error copying printout PDF from temporary directory!"
          echo "${printout_dsf_basename}.pdf" >>${RESULT_PDF_LIST_FILE}

          # A5 on A4, a A5+A5 spread on single A4 surface: Use 'awk' to create a
          # copy of the printout template file with changed input PDF file name
          # and then execute 'context' on the new file.
          printout_sss_basename="printout-EASY_${currentdoc_basename}-on-A4-sidebyside-simple"
          awk "/replace-this-filename.pdf/"' { gsub( "'"replace-this-filename.pdf"'", "'"${currentdoc_basename}.pdf"'" ); t=1 } 1; END{ exit( !t )}' "../../tex/printout-template_EASY-A5-on-A4-sidebyside-simple.context" >"${printout_sss_basename}.context" || die $? "[${currentdoc_basename}]: Error with 'awk' when creating sss printout!"
          local log09file="${logfileprefix}log-09_printout-sss.log"
          context "${printout_sss_basename}.context" 1>"${log09file}" 2>&1 || die_log $? "Error creating sss printout!" "${log09file}"
          cp "${printout_sss_basename}.pdf" "../../${RESULT_DIRNAME}/" || die $? "Error copying printout PDF from temporary directory!"
          echo "${printout_sss_basename}.pdf" >>${RESULT_PDF_LIST_FILE}
        fi
      fi
    fi

    # Check warnings in the logs

    lp_barwarning_count=$(grep -i "warning: barcheck" "${log01file}" | wc -l)
    overfull_count=$(grep -i "overfull" "${log07file}" | wc -l)
    underfull_count=$(grep -i "underfull" "${log07file}" | wc -l)
    fontwarning_count=$(grep -i "Font Warning" "${log07file}" | wc -l)
    if [ "${lp_barwarning_count}" -gt "0" ]; then
      echo -e "${PRETXT_DEBUG}${txt_docbase}: Lilypond bar check warnings: ${lp_barwarning_count}"
    fi
    if [ "${overfull_count}" -gt "0" ] || [ "${underfull_count}" -gt "0" ]; then
      echo -e "${PRETXT_DEBUG}${txt_docbase}: TeX warnings - overfull: ${overfull_count}, underfull: ${underfull_count}"
    fi
    if [ "${fontwarning_count}" -gt "20" ]; then
      echo -e "${PRETXT_DEBUG}${txt_docbase}: TeX warnings - font: ${fontwarning_count}; ${C_RED}CHECK THE LOG!!${C_RESET}"
      echo "Too many font warnings! There is a problem!" >>"${TOO_MANY_WARNINGS_FILE}"
    else
      [ "${fontwarning_count}" -gt "0" ] && echo -e "${PRETXT_DEBUG}${txt_docbase}: TeX warnings - font: ${fontwarning_count}"
    fi

  } # END compile_document_sub


  local document_basename="$1"

  # setup some UI text with colors (if enabled):
  local txt_docbase="${C_DGRAY}[${2}${1}${C_DGRAY}]${C_RESET}"
  local txt_doctex="${C_DGRAY}[${2}${1}.tex${C_DGRAY}]${C_RESET}"
  local txt_resultpdf="${C_DGRAY}[${2}${RESULT_DIRNAME}/${1}.pdf${C_DGRAY}]${C_RESET}"
  local temp_dirname_twolevels="${TEMP_DIRNAME}/${document_basename}"

  echo -e "${PRETXT_START}${txt_docbase}"

  # Test if we are currently in the correct directory:
  [ -f "./${document_basename}.tex" ] || die 1 "Not currently in the project's root directory!"

  # Ensure the result directory exists:
  mkdir -p "./${RESULT_DIRNAME}" 2>"/dev/null"
  [ -d "./${RESULT_DIRNAME}" ] || die $? "Could not create the result directory ./${RESULT_DIRNAME}."

  # Clean old build:
  [ -d "${temp_dirname_twolevels}" ] && rm -R "${temp_dirname_twolevels}"/* 2>"/dev/null"
  # Ensure the build directory exists:
  mkdir -p "${temp_dirname_twolevels}" 2>"/dev/null"
  [ -d "${temp_dirname_twolevels}" ] || die $? "Could not create the build directory ${temp_dirname_twolevels}."

  # Copy/link the required files to the temp directory (lilypond-book will copy
  # the rest of them):
  mkdir "${temp_dirname_twolevels}/content"
  cp -R "tex" "${temp_dirname_twolevels}/"
  cp "tags.can" "${temp_dirname_twolevels}/"
  # images are big (and not all of them are needed), so link instead of copy:
  ln -s "../../../content/img" "${temp_dirname_twolevels}/content/img"

  echo -e "${PRETXT_EXEC}${txt_docbase}: lilypond-book"

  # Run lilypond-book. It compiles images out of lilypond source code within tex
  # files and outputs the modified .tex files and the musical staff images
  # created by it to subdirectory ${temp_dirname_twolevels}. The directory
  # (last level only) is created if it doesn't exist. Note the need to include
  # the path for the log file, as we are not in the subdirectory yet.
  local log01file="log-01_lilypond.log"
  lilypond-book -f latex --latex-program=lualatex --output="${temp_dirname_twolevels}" "${document_basename}.tex" 1>"${temp_dirname_twolevels}/${log01file}" 2>&1 || die_log $? "Error running lilypond-book!" "${temp_dirname_twolevels}/${log01file}"

  # Enter the temp directory. (Do rest of the steps there.)
  cd "${temp_dirname_twolevels}" || die 1 "Cannot enter temporary directory!"


  compile_document_sub "$1" "$2" ""


  # Handle midi & mp3

  if [ ${midifiles} == "true" ] || [ ${audiofiles} == "true" ]; then
    which "python3" >"/dev/null" || die 1 "'python3' binary not found in path"
  fi
  if [ ${midifiles} == "true" ]; then
    echo -e "${PRETXT_EXEC}${txt_docbase}: unilaiva-copy-audio (copy midi files)"
    local cur_res_midi_subdirname="${RESULT_MIDI_DIRNAME}/${document_basename}"
    rm -R "${cur_res_midi_subdirname}"/* 2>"/dev/null"
    mkdir -p "../../${cur_res_midi_subdirname}" 2>"/dev/null"
    [ -d "../../${cur_res_midi_subdirname}" ] || die $? "Could not create the midi result directory ./${cur_res_midi_subdirname}."
    local log10file="log-10_copy-midi.log"
    # Execute the audio copy tool for midi files
    ../../tools/unilaiva-copy-audio.py3 --midi \
      "${document_basename}.dep" "../../${cur_res_midi_subdirname}" \
      1>"${log10file}" 2>&1 \
      || die_log $? "Error copying midi files to result directory" "${log10file}"
  fi
  if [ ${audiofiles} == "true" ]; then
    echo -e "${PRETXT_EXEC}${txt_docbase}: unilaiva-copy-audio (encode audio)"
    local cur_res_audio_subdirname="${RESULT_AUDIO_DIRNAME}/${document_basename}"
    rm -R "${cur_res_audio_subdirname}"/* 2>"/dev/null"
    mkdir -p "../../${cur_res_audio_subdirname}" 2>"/dev/null"
    [ -d "../../${cur_res_audio_subdirname}" ] || die $? "Could not create the audio result directory ./${cur_res_audio_subdirname}."
    local log11file="log-11_encode-audio.log"
    # Execute the audio copy tool for encoding audio files
    ../../tools/unilaiva-copy-audio.py3 --audio \
      "${document_basename}.dep" "../../${cur_res_audio_subdirname}" \
      1>"${log11file}" 2>&1 \
      || die_log $? "Error encoding audio files!" "${log11file}"
  fi

  # Create lyrics-only books, if so wanted

  if [ ${lyricbooks} == "true" ]; then
    grep '\\input{.*setup_.*\.tex}' "${document_basename}.tex" >"/dev/null"
    if [ $? -ne 0 ]; then
      echo -e "${PRETXT_NOEXEC}${txt_docbase}: Extra lyric-only book not created, as no '\input{setup_<...>}' in doc"
    else
      local lyricdoc_basename="${document_basename}_LYRICS-ONLY"
      cat "${document_basename}.tex" \
        | sed -e 's/\(\\input{.*setup_.*\.tex}\)/\\input{tex\/internal-lyricbook-presetup.tex}\1\\input{tex\/internal-lyricbook-postsetup.tex}/g' \
        >>"${lyricdoc_basename}.tex"
      rm ./idx_*.sxd ./idx_*.sbx 2>"/dev/null"
      compile_document_sub "${lyricdoc_basename}" "$2" "lyric-"
    fi
  fi

  # Clean up the compile directory: remove some temporary files.
  rm ./tmp*.out ./tmp*.sxc 2>"/dev/null"

  # Get out of ${temp_dirname_twolevels}:
  cd "${INITIAL_DIR}" || die $? "Cannot return to the main directory."

  echo -e "${PRETXT_DEBUG}${txt_docbase}: Build logs in ${temp_dirname_twolevels}/"
  echo -e "${PRETXT_SUCCESS}${txt_resultpdf}: Compilation successful!"

} # END compile_document()


# Copies the result .pdf's to the deploy directory ${DEPLOY_DIRNAME}, if:
#   - not inside Docker container
#   - deploy is not forbidden by command line argument
#   - deploy directory exists
#   - ${RESULT_PDF_LIST_FILE} exists and contains data
#   - pdf's filename does not contain _NODEPLOY
deploy_results() {
  [ -z "${IN_UNILAIVA_DOCKER_CONTAINER}" ] || return
  [ "${deployfinal}" = "true" ] || return
  [ -f ${RESULT_PDF_LIST_FILE} ] || return
  if [ ! -d "./${DEPLOY_DIRNAME}" ]; then
    echo -e "${PRETXT_NODEPLOY}Resulting PDF files NOT copied to ./${DEPLOY_DIRNAME}/ (directory not found)"
    return
  fi
  while IFS= read -r pdf_file; do
    if [[ ${pdf_file} == *"_NODEPLOY"* ]]; then
      echo -e "${PRETXT_NODEPLOY}${pdf_file} not deployed due to filename"
      continue
    fi
    [ -f "./${RESULT_DIRNAME}/${pdf_file}" ] || die 21 "Could not access ${pdf_file} for deployment"
    cp "./${RESULT_DIRNAME}/${pdf_file}" "./${DEPLOY_DIRNAME}/"
    [ $? -eq 0 ] || die 22 "Could not deploy ${pdf_file}"
    echo -e "${PRETXT_DEPLOY}${pdf_file} copied to ./${DEPLOY_DIRNAME}/"
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
lyricbooks="true"
midifiles="true"
audiofiles="true"
gitpull="false"
parallel="true"
shellonly="false"

setup_ui

doc_count=0 # will be increased when documents are added to 'docs' array

all_args="$@"

# Test program arguments:
while [ $# -gt 0 ]; do
  case "$1" in
    "--no-lyric")
      lyricbooks="false"
      shift;;
    "--no-midi")
      midifiles="false"
      shift;;
    "--no-audio")
      audiofiles="false"
      shift;;
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
    "--shell")
      shellonly="true"
      shift;;
    "-q")
      deployfinal="false"
      createprintouts="false"
      astralbooks="false"
      partialbooks="false"
      selections="false"
      lyricbooks="false"
      midifiles="false"
      audiofiles="false"
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
          *) die 1 "Given file does not have a .tex extension!"
        esac
        [ -f "${tmp}" ] || die 1 "Given file is not in the current directory!"
        tmp=${tmp%.tex} # remove the suffix
        docs[doc_count]=${tmp} ; ((doc_count++))
        # Compile only the given file, when files are explicitly given:
        mainbook="false"
        astralbooks="false"
        partialbooks="false"
        selections="false"
      else
        echo ""
        echo -e "${PRETXT_ERROR}Incorrect argument or nonexisting file name."
        print_usage_and_exit
      fi
      shift;;
  esac
done

[ -f "./compile-songbooks.sh" ] || die 1 "Not currently in the project's root directory!"

if [ -z "${IN_UNILAIVA_DOCKER_CONTAINER}" ]; then # not in container (yet)
  # Run git pull only if not in docker container, and if so requested
  if [ ${gitpull} = "true" ]; then
    which "git" >"/dev/null" || die 1 "'git' binary not found in path, but pull requested!"
echo -e "${PRETXT_GIT}Pulling remote changes (with rebase)..."
    git pull --rebase
    [ $? -eq 0 ] || die 5 "Cannot pull changes from git as requested."
  fi
  # If docker is requested, start the container and run this script there
  if [ ${usedocker} = "true" ]; then
    compile_in_docker ${all_args}
    retcode=$?
    [ ${retcode} -eq 0 ] || exit ${retcode}
    deploy_results
    echo ""
    echo -e "${TXT_DONE}"
    echo ""
    exit 0
  fi
else # we are in the container
  if [ ${shellonly} = "true" ]; then
    # If debug shell is requested, only run interactive shell and exit.
    echo -e "${PRETXT_DOCKER}Start interactive shell in the container only"
    bash
    exit 127
  fi
fi

# Test Bash version here and not earlier, to allow using the script with
# docker and MacOS (which has version 3 by default).
[ "${BASH_VERSINFO:-0}" -lt 4 ] && die 9 "Your Bash is too old; v4 or later required."

# Test executable availability:
which "lualatex" >"/dev/null" || die 1 "'lualatex' binary not found in path!"
which "texlua" >"/dev/null" || die 1 "'texlua' binary not found in path!"
which "lilypond-book" >"/dev/null" || die 1 "'lilypond-book' binary not found in path!"
which "awk" >"/dev/null" || die 1 "'awk' binary not found in path!"
which "sed" >"/dev/null" || die 1 "'sed' binary not found in path!"

# Create the 1st level temporary directory in case it doesn't exist.
mkdir "${TEMP_DIRNAME}" 2>"/dev/null"
[ -d "./${TEMP_DIRNAME}" ] || die 1 "Could not create temporary directory ${TEMP_DIRNAME}."

# Remove the files signifying the last compilation had problems,
# if they exist:
rm "${TOO_MANY_WARNINGS_FILE}" >"/dev/null" 2>&1
rm "${RESULT_PDF_LIST_FILE}" >"/dev/null" 2>&1

# Trap interruption (Ctrl-C):
trap 'die 130 Interrupted.' INT
# trap TERM signal. When a subprocess encounters an error, it sends this signal
# to the main process.
trap 'die 99 "Terminated (most likely asked by subprocess)"' TERM

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


[ -z ${IN_UNILAIVA_DOCKER_CONTAINER} ] \
  && dockerized_text="NO ${C_YELLOW}(this is not recommended!)" \
  || dockerized_text="YES"
[ ${parallel} = "true" ] \
  && parallel_text="YES ${C_RESET}(maximum concurrency: ${MAX_PARALLEL})" \
  || parallel_text="NO"
[ ${doc_count} = 1 ] && parallel_text="NO ${C_RESET}(1 document only)"
[ ${createprintouts} = "true" ] \
  && createprintouts_text="YES" \
  || createprintouts_text="NO"
[ ${lyricbooks} = "true" ] \
  && lyricbooks_text="YES" \
  || lyricbooks_text="NO"
[ ${midifiles} = "true" ] \
  && midifiles_text="YES" \
  || midifiles_text="NO"
[ ${audiofiles} = "true" ] \
  && audiofiles_text="YES" \
  || audiofiles_text="NO"
[ ${deployfinal} = "true" ] \
  && deployfinal_text="${C_YELLOW}YES" \
  || deployfinal_text="NO"

echo ""
echo -e "Compiling Unilaiva songbook(s):"
echo ""
echo -e "  - Documents to compile: ${C_WHITE}${doc_count}${C_RESET}"
echo -e "  - Using Docker: ${C_WHITE}${dockerized_text}${C_RESET}"
echo -e "  - Parallel compilation: ${C_WHITE}${parallel_text}${C_RESET}"
echo -e "  - Additional lyrics only versions: ${C_WHITE}${lyricbooks_text}${C_RESET}"
echo -e "  - Printouts: ${C_WHITE}${createprintouts_text}${C_RESET}"
echo -e "  - Midi: ${C_WHITE}${midifiles_text}${C_RESET}"
echo -e "  - Audio: ${C_WHITE}${audiofiles_text}${C_RESET}"
echo -e "  - Deploy: ${C_WHITE}${deployfinal_text}${C_RESET}"
echo ""


# Compile the documents in the 'docs' array:
running_count=0
runs_started=0
doc_color_idx=0
for doc in "${docs[@]}"; do
  [ ${doc_color_idx} -ge ${DOC_COLOR_COUNT} ] && doc_color_idx=0
  compile_document "${doc}" "${DOC_COLORS[doc_color_idx]}" &
  ((runs_started++))
  ((running_count++))
  ((doc_color_idx++))
  if [ ${parallel} = "true" ]; then
    if [ ${running_count} -eq ${MAX_PARALLEL} ]; then
      wait -n # wait for any job to finish
      ec=$?
      [ ${ec} -ne 0 ] && die ${ec} "(BUG) Error in compile script, should not happen"
      ((running_count--))
    fi # else continue loop
  else
    wait # wait for all (= the last) compile_document to finish
    ec=$?
    [ ${ec} -ne 0 ] && die ${ec} "(BUG) Error in compile script, should not happen"
    ((running_count--))
  fi
done

wait # wait for all jobs to end, returns always 0

deploy_results

cleanup

if [ -e "${TOO_MANY_WARNINGS_FILE}" ]; then
  echo ""
  echo -e "${C_YELLOW}!!! WARNING !!!${C_RESET}"
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
  echo -e "${TXT_DONE}"
  echo ""
else # we're in docker
  echo -e "${PRETXT_DOCKER}Stop compiler container..."
fi

exit 0
