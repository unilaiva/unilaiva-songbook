unilaiva-songbook
=================

Unilaiva-songbook is a collection of song lyrics, musical information, etc.,
and a system to create songbooks out of this data, for the contributors'
private use. The system is written [LaTeX](https://www.latex-project.org/).

**The PDFs compiled from these sources are available at
[https://unilaiva.aavalla.net/](https://unilaiva.aavalla.net/)**



Compiling the songbooks to create PDF documents
-----------------------------------------------

If you are on a UNIX-compatible system (e.g. Linux, MacOS or Windows WSL),
you can use the provided `compile-songbooks.sh` shell script to build the
books. By default, if run without arguments, it builds all the books
contained in this repository, each with all supported extra formats.
For information about its usage, run: `compile-songbooks.sh --help`

Otherwise you must do the compilation steps manually, see **Option THREE**.


### Option ONE: use the script with Docker (recommended) ###

This works on Linux and MacOS, or Windows with WSL. Using Linux is
recommended, as it is the most tested of the operating systems.

Simply execute the compilation script without arguments.

This guarantees the best results, as the actual compiling is done in a Docker
container that has all the correct packages installed and configured correctly.

Note that the first run will take a long time, as the Docker image is built
and all the required software downloaded (about 1100 MiB) and installed into it.
When built, the image requires about 2,5 GiB of disk space. Subsequent runs
will be fast as they use the already built image.

By default the compile script uses a maximum of 6 GiB of memory when running
6 parallel compilations (the default maximum for parallelism). On low memory
systems, use the `--sequential` option for the compile script to compile
one document at a time.

##### Requirements #####

This method requires the following software installed on your system:
  * `docker`
  * `bash` (installed by default on most systems)
  * `git` (recommended for initially retrieving the songbook source)
  * ...and 2,5 GiB of disk space (for Docker image)

##### Example: on Debian or Ubuntu Linux, using Docker #####

To install the dependencies, download the project's source and compile
the songbook using a Docker container, you need to run the following
commands:

  1. `sudo apt install docker.io git`
  2. `sudo adduser <USERNAME> docker` # replace <USERNAME> with your username
  3. `su <USERNAME>` # relogin for the group setting to become active (or reboot)
  4. `git clone --depth 1 https://github.com/unilaiva/unilaiva-songbook.git`
  5. `cd unilaiva-songbook`
  6. `./compile-songbooks.sh`

This procedure was tested on Ubuntu versions 23.03, 23.10 and 24.04.

##### Example: on Arch Linux, using Docker #####

  1. `sudo pacman -Suy docker`
  2. `sudo gpasswd -a <USERNAME> docker` # replace <USERNAME> with your username
  3. `sudo systemctl enable docker.socket`
  3. `su <USERNAME>` # relogin for the group setting to become active (or reboot)
  4. `git clone --depth 1 https://github.com/unilaiva/unilaiva-songbook.git`
  5. `cd unilaiva-songbook`
  6. `./compile-songbooks.sh`

This procedure was tested on up-to-date Arch Linux, a rolling release, on
2024-04-30.

##### Example: on MacOS, using Docker #####

This is tested with MacOS Ventura 13.2.1 on an Intel system, but should work
on other OS versions and also on ARM systems.

First, install Docker Desktop from <https://docs.docker.com/desktop/install/mac-install/>.

Next, install [Homebrew](https://brew.sh/) and using it, Bash (the Bash version
included in MacOS by default is too old):
```sh
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
  # Follow instructions given by this command for setting PATH
  brew install bash
```

**Optional:** To enable automatic building of the Docker image in case it is
later updated, you also need GNU's version of `date`. To get it, run
`brew install coreutils`. The GNU version will be installed as `gdate`, and the
compiler script will use it if it exists. On first run of the compile script,
the Docker image is built regardless of this, and later, if the image is
updated, you can alternatively trigger a rebuild manually by invoking
`./compile-songbooks.sh --docker-rebuild`.

Then start the command prompt and run the following commands:
  1. `git clone --depth 1 https://github.com/unilaiva/unilaiva-songbook.git`
  2. `cd unilaiva-songbook`
  3. `./compile-songbooks.sh`
  
If `git` is not installed, it will be automatically installed by the OS when
trying to run it for the first time.

##### Example: on Windows, using Docker #####

One must use Windows Subsystem for Linux (WSL). TODO: write instructions.


### Option TWO: use the script without Docker ###

If you don't want to use Docker, you can install the required packages and
execute the compilation script with `--no-docker` option.

##### Requirements #####

These dependencies are included in the Docker image, and need be installed on
the host system only if compiling without using the Docker image.

  * Newish LaTeX 2e distribution (TeX Live 2023 is recommended) with some fairly
    standard packages and the binaries `lualatex` and `texlua`. If you use an
    older LaTeX distribution, you might have a problem with incorrect line
    breaking within songs, which can be corrected by deleting the rewrite
    of \SB@obeylines macro in the unilaiva-songbook-common.sty file.
  * Lilypond installation version 2.24.3 (or probably any later one) with the
    binary `lilypond-book`
  * Fonts 'Noto Sans' and 'Noto Serif', with medium and extrabold weights
  * Locale 'fi_FI.utf8'
  * `bash` (installed by default on most systems)
  * `git` (recommended for retrieving and updating the songbook source)
  * *Optionally* `context` or `contextjit` for creating versions for printing
    A5 size on A4 paper; (Using this might require executing `mtxrun --generate`
    before running the compile script.)
  * *Optionally* `ffmpeg` and `fluidsynth` for encoding mp3 audio from Lilypond
    sources
  * *Optionally* `pdftoppm` from poppler-utils and `convert` from imagemagick
    to extract the cover page of produced PDF as raster image file for e.g.
    website

Our project requires only some pretty standard LaTeX packages, which are
included in many LaTeX installations by default, to be installed on the system.
They are all included with `\usepackage` commands in the beginning of file
`tex/unilaiva-songbook_common.sty`.

One of the package dependencies, [songs](http://songs.sourceforge.net/), is
included in the project tree and used instead of a one possibly installed on
the system. This is because of compatibility reasons to ensure a specific
version: the package is used heavily and some of its macros are redefined.

##### Example: on Ubuntu 24.04, without Docker #####

Note that earlier Ubuntu versions than 23.04 require a change in the songbook
system's source. See the Requirements section above.

On Ubuntu 24.04 (noble), to install the dependencies, to download the
project's source and to compile the songbook without Docker, you need to run
the following commands:

  1. `sudo apt update && sudo apt install bash locales git context
     context-modules ffmpeg fluidsynth fluid-soundfont-gm fonts-noto-core
     fonts-noto-extra fonts-noto-mono imagemagick lilypond poppler-utils
     python3 texlive texlive-font-utils texlive-lang-arabic texlive-lang-english
     texlive-lang-european texlive-lang-portuguese texlive-lang-spanish
     texlive-latex-base texlive-latex-extra texlive-luatex texlive-music
     texlive-plain-generic`
  2. `sudo locale-gen fi_FI.utf8`
  3. `sudo mtxgen --generate`
  4. `git clone --depth 1 https://github.com/unilaiva/unilaiva-songbook.git`
  5. `cd unilaiva-songbook`
  6. `./compile-songbooks.sh --no-docker`

Some of the dependency packages are already installed by default.

##### Example: on Arch Linux, without Docker #####

On Arch Linux (on 2024-04-30), to install the dependencies, to download the
project's source and to compile the songbook without Docker, you need to run
the following commands:
  1. 'sudo pacman -Sy bash ffmpeg fluidsynth git imagemagick lilypond
     noto-fonts noto-fonts-extra poppler python soundfont-fluid texlive-context
     texlive-fontsextra texlive-fontsrecommended texlive-fontutils
     texlive-langarabic texlive-langenglish texlive-langeuropean
     texlive-langportuguese texlive-langspanish texlive-latex texlive-latexextra
     texlive-latexextra texlive-latexrecommended texlive-luatex texlive-music
     texlive-plaingeneric'
  2. Edit `/etc/locale.gen` and uncomment (or add) this line: `fi_FI.UTF-8 UTF-8`,
     and run `sudo locale-gen`
  3. `git clone --depth 1 https://github.com/unilaiva/unilaiva-songbook.git`
  4. `cd unilaiva-songbook`
  5. `./compile-songbooks.sh --no-docker`

Some of the dependency packages are already installed by default.


### Option THREE, compile manually ###

This option is for compiling manually without using the compile script nor
Docker. This way is not recommended. 

Here is **only** described how to build the main document of Unilaiva Songbook.
To build the others, these instructions must be modified. To create also the
collated printout versions (for printing A5 size on A4 paper), and to create
audio files from Lilypond sources, see the compile script.

Ensure you have all the dependencies installed (see **option TWO**) and the
project's source downloaded, and then run the following commands or their
equivalents in this exact sequence in the project's root directory:

  1. `lilypond-book -f latex --latex-program=lualatex --output=temp
     unilaiva-songbook_A5.tex`
  2. `cd temp ; ln -s ../tex ./ ; ln -s ../../content/img ./content/ ;
     ln -s ../tags.can ./`
  3. `lualatex unilaiva-songbook_A5.tex` # (1st time)
  4. `texlua tex/ext_packages/songs/songidx.lua -l fi_FI.utf8
     idx_title.sxd idx_title.sbx`
  5. `texlua tex/ext_packages/songs/songidx.lua -l fi_FI.utf8
     idx_auth.sxd idx_auth.sbx`
  6. `texlua tex/ext_packages/songs/songidx.lua -l fi_FI.utf8 -b tags.can
     idx_tag.sxd idx_tag.sbx`
  7. `lualatex unilaiva-songbook_A5.tex` # (2nd time)
  8. `lualatex unilaiva-songbook_A5.tex` # (3rd time)

**Explanation:** Lilypond will create a subdirectory called `temp`, create the
music notation images there, and copy `.tex` files there also (with necessary
modifications for displaying the notation). Rest of the compilation process
happens within that directory. Lilypond does not copy all needed files, so we
need to link them within the `temp` directory, to create directory structure
equivalent to the one in the project's root. Instead of linking with `ln -s`,
you can copy the files, but need to remember to do it every time modification
to the source is made, and new compilation is required. Then `lualatex` is run,
the indexes created, and finally `lualatex` is executed two more times. You
actually **do** need all three cycles of `lualatex` to get everything right.
In the end, you will have the result document, `unilaiva-songbook_A5.pdf` in the
`temp` directory. Use similar procedure for other `.tex` documents in the
project's root.

It is recommended to use `lualatex` engine, but with a little tweaking it is
also possible to compile with other LaTeX engines.



Printing
--------

These instructions are for printing the main Unilaiva Songbook. For other A5
books, the process is the same (except for file names).

The book is designed to be in **paper size A5** (148 mm x 210 mm), preferably
double-sided. It looks good as black and white, but color printing gets better
results (while using the non-black colors sparingly).

You can simply print the main document, `unilaiva-songbook_A5.pdf`. A5 paper ought
to be used (and selected in the printing software). Otherwise you will get big
scaled up pages or pages with wide margins.

If printing double sided, ensure that the pages face each other in such a way
that odd pages are on the right side (recto) and even pages are on the left
side (verso) of a spread. That order minimizes flipping pages within a song, as
all songs spanning at least two pages start from an even page. Also, the
margins, page number positions etc. are optimized for that order.

Note that margins ought to be set to zero in the printing software and the
printer drivers setup, if such options are available. On Linux and MacOS, the
`lp` program is recommended for printing without extra margins. Simply state
e.g. `lp -o PageSize=A4 printout-BOOKLET_unilaiva-songbook_A5-on-A4-doublesided-needs-cutting.pdf`
without the `fit-to-page` option that some GUI programs like to pass to it.

There are also special printing options, like printing multiple A5 sized pages
on an A4 sized paper. They are defined in files named
`printout-template_*.context` and are to be inputted to *ConTeXt*
program, which needs to be installed on the system. They operate on a previously
compiled `unilaiva-songbook_A5.pdf` file. See comments in the beginning of each
such file. If the compilation script finds the `context` or `contextjit`binary,
it will by default process these too, and use them as templates to create
similar printouts of the two-booklet version of the songbook as well.

#### Printing double sided on a single sided printer ####

To print double sided on a printer without a duplexer, one needs to print odd
pages first, then flip each page around, feed them to the printer, and then
print the even pages. With the main document, `unilaiva-songbook_A5.pdf`, the
pages need to be flipped on the long edge. The other files, named
`printout-*unilaiva-songbook*.pdf`, with multiple pages on an A4 sheet, should be
flipped on the short edge.

To flip pages *on the short edge* manually: put the printed stack of papers in
front of you upside down (printed side unseen), make a new stack by moving each
sheet from the top of the old stack to the top of the new stack (do not turn in
any way, just "translate"), one by one. Feed the new stack to the printer. Be
careful to put it in there in the correct way.

If your printing software is limited, you can extract odd and even pages with,
for example, `pdftk` like this:

  * `pdftk unilaiva-songbook_A5.pdf cat 1-endodd output unilaiva-songbook_odd.pdf`
  * `pdftk unilaiva-songbook_A5.pdf cat 1-endeven output unilaiva-songbook_even.pdf`

#### larva's example procedure for printing ####

This procedure prints the whole book on A4 sized papers with a printer capable
of single-sided printing only. Flipping pages, cutting and binding are done by
hand. The end result is a book consisting of two-sided A5 pages, which is the
preferred format.

  1. `./compile-songbooks.sh`
  2. `pdftk printout-BOOKLET_unilaiva-songbook_A5-on-A4-doublesided-needs-cutting.pdf cat
     1-endodd output unilaiva-songbook_odd.pdf`
  3. `pdftk printout-BOOKLET_unilaiva-songbook_A5-on-A4-doublesided-needs-cutting.pdf cat
     1-endeven output unilaiva-songbook_even.pdf`
  4. `lp -o PageSize=A4 unilaiva-songbook_odd.pdf`
  5. Flip the pages manually on the short edge and feed them to the printer.
  6. `lp -o PageSize=A4 unilaiva-songbook_even.pdf`
  7. Cut the A4 pages in half to get the A5 pages and put them in correct
     order.
  8. Punch holes and bind the book.


Project structure and guidelines
--------------------------------

#### Directory structure ####

```
├── **content**
│   └── **img**
├── **deploy**
├── **docker**
│   └── **songs**
├── **result**
├── **tex**
│   ├── **ext_packages**
│   ├── printout-template_BOOKLET-A5-on-A4-doublesided-needs-cutting.context
│   ├── printout-template_EASY-A5-on-A4-sidebyside-simple.context
│   ├── ul-selection_example.tex
│   ├── ul-selection_include.tex
│   ├── unilaiva-songbook_common.sty
│   ├── unilaiva-songbook_content_include_part1.tex
│   ├── unilaiva-songbook_content_include_part2.tex
│   └── unilaiva-songbook_content_include_part3_appendices.tex
├── **workspace**
├── compile-songbooks.sh
├── README.md
├── tags.can
├── **temp**
├── ul-selection_*.tex
├── unilaiva-astral*.tex
├── unilaiva-songbook_part1.tex
├── unilaiva-songbook_part2.tex
└── unilaiva-songbook_A5.tex
```
*(All the files are not included in this representation.)*

Project's main file is `unilaiva-songbook_A5.tex`. It is used to create the full
songbook. There are also `unilaiva-songbook_part1.tex` and
`unilaiva-songbook_part2.tex`, which together provide such a version of the
book, where the content is divided into two parts, booklets, for binding
reasons.

`tex` subdirectory contains partial LaTeX files, which are included in the main
document(s) with `\input` macros. There resides also the most important
`unilaiva-songbook_common.sty` package, which contains all the needed imports,
definitions, settings and style used in the songbook. It is imported to the
main document(s) with `\import` macro. `context` files used to create special
printout versions reside there as well. `ul-selection_include.tex` is a file to
be included in song selection booklets.

Song data and other *content* will be in various files inside `content`
subdirectory and will be inputed into the main file. Images are put into
`content/img`.

`ul-selection*.tex` define song selection booklets. They contain only some of
the songs of the full songbook. All files in the project's root matching this
filename pattern will be automatically compiled by the compile script. See
`tex/ul-selection_example.tex` for an example.

There are also various 'Unilaiva no Astral' books, named `unilaiva-astral*.tex`.

External packages are in `tex/ext_packages` subdirectory. This currently
includes only the `songs` package and it's documentation.

The compilation script will place the final PDF files in the `result` directory.

`workspace` subdirectory contains template files useful for transcribing work.

Code lines in the source ought to be maximum of 100 characters long, but
exceptions are allowed when needed, especially for song data.


Adding and editing songs
------------------------

To begin, see the already existing songs in `content` directory. Also, it is
a good idea to take a look at `songs` package documentation. It is included as
a PDF file in `tex/ext_packages/songs/songs.pdf`. It can also be viewed online at
[http://songs.sourceforge.net/songsdoc/songs.html](http://songs.sourceforge.net/songsdoc/songs.html).

Below we're explaining mostly Unilaiva-specific things, so understanding how
`songs` package works is beneficial.

Stuff inside `songs` environment (the files in `content` directory named with
a prefix `songs_`) ought to contain only individual songs (and data related to
them) between `\beginsong` and `\endsong` macros plus other data wrapped in
`intersong` environments.

#### General instructions ####

The main document must have an `\input` instruction for a file named
`setup_<...>.tex`, and this file must be where `unilaiva-songbook_common.sty`
package is loaded. This is required for automatically creating a lyrics-only
version of the document. You can copy the file
`tex/setup_default-A5-fullmusic_include.tex` and make your own version, but
the filename must start with `setup_` to allow for automatic creation of
lyric-only book version.


#### Page and line breaks ####

The `songs` package does a very good job in organising the songs for a nice
output, but sometimes it needs a little bit of help.

Use `\brk` in a lyric line to suggest a good breaking point, if the whole line
doesn't fit on one line in the output.

`\brk` can be used between verses and songs, too, to suggest a good spot for
a page (or column, if using more than one) brake.

To **force** a page break, use `\sclearpage` or `\scleardpage` between songs;
the first hops to the next page and the latter jumps to the next spread
(even page). These (or `\brk`, `\hardbrk`, `\forcebrk`) are sometimes needed
right before a song longer than a spread, to correctly end the previous song
with a horizontal line.


### Repeats ###

There are two ways to signify repeating sections.

The inline repeat macros `\lrep` (left mark) and `\rrep` (right mark) are marks
that can be put anywhere, including in the middle of lyric lines. Additionally,
`\rep{<n>}` can be added e.g. after the right mark to signify the number of
repeats <n>.

The other way is to use vertical bars on the left of the lyric lines to inform
that those lines are to be repeated. These bars can span multiple lines and
support nesting with multiple lines. Put the repeated section between
`\beginrep` and `\endrep` inside a verse. Example:

```tex
\beginsong{My Song}
  \beginverse
    \beginrep
      Here are lyrics for the verse
      That is completely repeated.
    \endrep
  \endverse
  \beginverse
    This lyric line has no repeats
    \beginrep
      These two lines have
      one repeat bar sign
      \beginrep
        This line has two levels of repeats
      \endrep
    \endrep
  \endverse
\endsong
```

One repeat bar is usually used to signify that the part is sung two times. To
mark a different amount of repetitions, you can e.g. use the previously
discussed `\rep{<n>}` macro at the last line of the repeated section, or you
can use `\prep{<n>}` which creates a repeat number on it's own line. This is
meant to be used right after `\beginrep`.

Also, you can mark spots from where to jump to a different part of the song with
`\goto{Beginning words of the verse}`.

Please note that \beginchorus...\endchorus of the original `songs` package is
not supported in this system to signify repeating parts.


### Measure bars ###

Use measure bar lines `|` (the pipe character) to mark only the beginning of
each measure, never the end. If a line ends on a measure that has no lyrics on
the same line, use ` \e` macro to highlight that there indeed is a measure
there, which might or might not continue on the next line. `\e` will be replaced
with a dash in the final document, if it also has measure bar lines in it, and
will be ignored in case it hasn't (as is the case with 'lyric' songbooks without
chords). So the policy is this: one bar line per bar!

To turn off measure bars from the final document, use `\measuresoff`.


### Chords ###

Chords are set with `\[x]` commands (replace *x* with the chord), which are
mixed in with the lyrics. The chord appears above the word of lyrics that is
immediately after (without space) the chord definition. Melodies and beats
are also defined within `\[]` commands, as explained further down.


### Melodies ###

#### Full melodies ###

Full melodies are written using `lilypond` syntax. It produces actual sheet
music and MIDI files. See documentation in
[http://lilypond.org/](http://lilypond.org/). `lilypond` parts must be put
outside of verses (but inside of a song), and wrapped within `lilywrap`
environment. See examples in `content_songs_*.tex`.

##### Note on converting lyrics from Lilypond to songbook format #####

To convert lyrics from Lilypond to the format used by this songbook, (at least)
the following string replacements ought to be done in the following order:

 1. " -- | " -> "|"
 2. " -- _ " -> ""
 3. " -- " -> ""
 4. " | " -> " |"
 5. " __" -> ""
 6. " _" -> ""
 7. "__ " -> ""
 8. "|_" -> "|"
 9. "\skip 1 " -> ""
10. "\"\" " -> ""
11. "~" -> "\jw "
12. "\altcol " -> ""

Be careful with the whitespaces!

If you are using Unilaiva-specific Lilypond style with `theLyricsOne` etc. to
present lyrics in your Lilypond, you can use `tools/unilaiva-lyrics-lp2tex.py3`
script to do the conversion. Run it without arguments for usage information.

#### Melody hints on the chord line ####

The `\mn???` commands display an encircled note name hint above the chord
line. They are meant to display (sung) melody notes above the lyrics. It would
be nice to have the first (non-unison) interval for each song to help
remembering of the song.

The commands must be called from within a chord definition. The note name must
be written as upper case for transposing to work, even though the result is
actually presented in lower case.

To disable showing of the notes for the whole document, set `\shownotesfalse`
in the main document preamble (after including
`tex/unilaiva-songbook_common.sty`).

Call `\notesoff` command between verses to disable showing of notes in the
following verses of that song.

The recommended use for this feature is to at least display the first sung
non-unison melody interval of each song. So just specify the first two melody notes and
use `\notesoff` after the first verse.

Choose the correct variant:

  * `\mn{<note>}`                     : on verse's first line
  * `\mnc{<note>}`                    : on verse's first line, above a chord
  * `\mncii{<note>}{<note>}`          : on first line, 2 notes, above a chord
  * `\mnciii{<note>}{<note>}{<note>}` : on first line, 3 notes, above a chord
  * `\mnd{<notename>}`                : on other lines of a verse

Use `\mn`, `\mnc`, `\mncii` or `\mnciii` to display notes on the first line of
lyrics (elsewhere they would overlap the lyrics on the line above)). Use `\mn`
if the note is not to be displayed at the exact same horizontal spot as a
chord, and use `\mnc` to display a note and a chord on top of each other: in
that case you must put the chord immediately after the `\mnc` command within
the same chord definition brackets.

`\mncii` and `\mnciii` are two and three note extensions of `\mnc`: with them
one can put two or three notes on top of one chord. They are also meant to be
used only on the first line of lyrics in a verse.

`\mnd` puts the note at about same height as chords, so it can be used in any
line in the lyrics with the caveat, that chords and notes are put beside each
other.

If you wish to have melody hints above the chord line throughout all lines of
a verse, begin the verse with `\mnbeginverse`. It adjusts line spacing to allow
for all melody note variants.

There are `\ma*` macros also that are similar to `\mn*` macros, except that
they print the note in an alternate color. `\mauii` and `\madii` macros allow
for printing normal and alternate notes on top of each other.

Example usage:

```
  \[\mnc{A}Am]Love is \[\mn{E}]great
  and \[\mnd{D#}]food tastes \[\mnd{A}]good

  \[\mnciii{C}{A}{F}Fmaj7]Tralalaa
```

### Beat marks ###

If neede, spots for beats can be marked with `\bm???` commands within chord
definitions `\[]`, too. The beats appear as small dots in chord color above
the lyrics, just below the baseline of the chords.

Use `\bm`, when the beat mark is by itself (without chord or melody note).

Use `\bmc` when you want to put the mark at the same horizontal space, on top
of each other, with a melody note and/or a chord. In such a case `\bmc`
should always be before the chord. and the recommended order is: beat mark,
melody note, chord. If `\bm` or `\bmc` is followed immediately by a chord,
there must be a space between them.

`\bmadj` and `\bmcadj{}` are variations which take one mandatory parameter in
curly braces: a horizontal adjustment of the mark position as a dimension.
`\bmadj{-.5ex}` moves the mark about half a character width left from where it
would appear without adjustment, and `\bmadj{.5ex}` moves it to the right.

To disable showing of the beats for the whole document, set `\showbeatsfalse`
in the main document preamble after package imports.

Call `\beatsoff` command between verses to disable showing of notes in the
following verses of the song. `\beatson` puts them back for the next verses
(unless `\showbeatsfalse` is set in the main doc).

Example usage:

```
  |\[\bmc Am]Love \[\bm]is |\[\bmc E]great \[\bm]
  and |\[bm]food \[bm]tastes |\[\bmc Am]good \[\bm]

  \[\bmc\mnc{C}C]Trallallaaa
```

### Tags ###

Tags can be attached to songs by defining `tags=` keyval argument for
`\beginsong` macro. An example: `\beginsong{Song name}[tags={love, smile}]`.

All tags must be listed in file `tags.can` before they can be used.

To disable tags totally, put `\showtagsfalse` in the main document preamble
after package imports.

The tag index is found at the end of the result document.


#### More information ####

...can be found in `tex/unilaiva-songbook_common.sty` file. There are special
hidden undocumented features! ;)


Creating song selections
------------------------

It is very easy to create booklets with only specific selected songs. See file
`ul-selection_example.tex` for an example and documentation. The compile script
will assume any file with a name `ul-selection_*.tex` in the project's root to
be a song selection booklet and will compile it.


Tentative TODO
--------------

*  Add more songs
*  Add translations and explanations for existing songs
*  Improve existing translations and explanations
*  Improve the introduction for mantras and the Finnish mythology section
*  Review tags and add more of them
*  Review phases
*  Organize songs better and decide the categories (= chapters / parts)
*  Possibly add poems, prayers etc in between songs or in their own category(?)
*  Further develop visual style of the end document
