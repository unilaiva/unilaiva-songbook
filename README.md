unilaiva-songbook
=================

unilaiva-songbook is a collection of song lyrics etc for the contributors' 
private use.

The PDF compiled from these sources is available on
[https://unilaiva.aavalla.net/](https://unilaiva.aavalla.net/)


Environment
-----------

unilaiva-songbook is a project written in LaTeX.

#### Requirements ####

  * Standard LaTeX installation with some standard packages and the binaries
    `pdflatex` and `texlua`
  * Lilypond installation with the binary `lilypond-book`
  * Font 'Noto'; on Debian, it is in package `tex-fonts-extra`


Our project requires only some pretty standard LaTeX packages, which 
are included in many LaTeX installations by default, to be installed on 
the system. They are all included with `\usepackage` commands in the 
beginning of the project's main file: `unilaiva-songbook.tex`.

One of the package dependencies, `songs`, is included in the project
tree and used instead of a one possibly installed on the system. This 
is because of compatibility reasons to ensure a certain version: the 
package is used heavily and some of its commands are redefined.


Creating a PDF document
-----------------------

If you're on an UNIX system, you can simply use the provided 
`compile_unilaiva-songbook.sh` shell script to build a PDF document 
out of our project.

Otherwise, you should to run binaries in the following sequence:
`lilypond-book`, `pdflatex`, `texlua songidx.lua` (for song titles),
`texlua songidx.lua` (for authors), `texlua songidx.lua` (for tags),
and `pdflatex` again.


Printing
--------

You can simply print the main document, `unilaiva-songbook.pdf`. It is of A5 
size. 

If printing double sided, ensure that the pages face each other in such a way 
that odd pages are on the right side (recto) and even pages are on the left 
side (verso) of a spread.

Note that margins ought to be set to zero in the printing software and the
printer drivers setup, if such options are available. On Linux and MacOS,
the `lp` program is recommended for printing without extra margins. Simply state
e.g. `lp -o PageSize=A4 printout_unilaiva-songbook_A5_on_A4_doublesided_folded.pdf`
without the `fit-to-page` option that many GUI programs pass to it.

There are also special printing options, like printing multiple A5 sized pages on
an A4 sized paper. They are defined in files named `printout_unilaiva-songbook*.context`
and are to be inputted to ConTeXt program, which needs to be installed on the system.
They operate on a previously compiled `unilaiva-songbook.pdf` file. See 
comments in the beginning of each such a file.

#### Printing double sided on a single sided printer ####

To print double sided on a printer without a duplexer, one needs to print odd
pages first, then flip each page around, feed them to the printer, and then print
the even pages.

To flip pages manually: put the printed stack of papers in front of you upside down
(printed side unseen), make a new stack by moving each sheet from the top of the old stack
to the top of the new stack (do not turn in any way, just "translate"), one by one.
Feed the new stack to the printer. Be careful to put it in there the right way.

If your printing software is limited, you can extract odd and even pages with `pdftk`
like this:
  * `pdftk unilaiva-songbook.pdf cat 1-endodd output unilaiva-songbook_odd.pdf`
  * `pdftk unilaiva-songbook.pdf cat 1-endeven output unilaiva-songbook_even.pdf`

#### larva's example procedure for printing ####

This procedure prints the whole book on A4 sized papers with a printer capable of
single-sided printing only. Flipping pages, cutting and binding are done by hand.
The end result is a book consisting of two-sided A5 pages, which is the preferred
format.

  * `./compile_unilaiva-songbook.sh`
  * `pdftk printout_unilaiva-songbook_A5_on_A4_doublesided_folded.pdf cat 1-endodd output unilaiva-songbook_odd.pdf`
  * `pdftk printout_unilaiva-songbook_A5_on_A4_doublesided_folded.pdf cat 1-endeven output unilaiva-songbook_even.pdf`
  * `lp -o PageSize=A4 unilaiva-songbook_odd.pdf`
  * flip pages manually and feed them to the printer
  * `lp -o PageSize=A4 unilaiva-songbook_even.pdf`
  * cut the A4 pages in half to get the A5 pages
  * order the pages
  * punch holes and bind


Project structure and guidelines
--------------------------------

Project's main file is `unilaiva-songbook.tex`. It includes all the
other files in the project and contains configuration.

Long `\renewcommand`s ought to be put into `unilaiva-songbook-extra.tex`
to maintain readability of the main file.

Song data and other *content* will be in various files inside `content`
subdirectory and will be inputed into the main file. Images are put into
`content/img`.

External packages (only `songs` for now) are in `ext_packages` subdirectory.

See `songs` package documentation in [http://songs.sourceforge.net/songsdoc/songs.html](http://songs.sourceforge.net/songsdoc/songs.html).

Stuff inside `songs` environment (the files in `content` directory named
with a prefix `songs_`) ought to contain only individual songs (and data 
related to them) between `\beginsong` and `\endsong` macros plus other 
data wrapped in an `intersong` environment. 

Use `\sclearpage` to jump to the beginning of a new page and `\scleardpage` to
hop to the beginning of a new left-side page. Suggest a good page brake spot
with `\brk`. These are mostly not needed, as `songs` package does quite a good
job in deciding these.

Lines ought to be less than 100 characters long (is anyone using 80 column
terminals still?), unless it is too much trouble.


### Measure bars and beats ###

If using measure bars and a measure ends at the end of a lyric line, put
a bar line `|` to *both* the end of the lyric line and the beginning of the 
next one (if one exists). If a measure in the end of a lyric line continues
into the next line, but there are no lyrics after the last bar line on the
first lyric line, add ` -` after the last bar line on the first line to signify
that there indeed is a (partial) measure, like this: `| -`

If it is necessary to mark beats, use `.` as a chord name, like this: `\[.]`.
Also underlining for lyrics can be used as a last resort.

### Melodies ###

Full melodies are written using `lilypond` syntax. See documentation in 
[http://lilypond.org/](http://lilypond.org/). It seems best to put `lilypond`
parts outside of verses (but inside of a song) to ensure correct line breaking.

### Repeats and choruses ###

By putting a verse between `\beginchorus` and `\endchorus` instead of `\beginverse`
and `\endverse`, a vertical line will be shown on the left side of the verse in
question. In this songbook that visual que is used to mark an immediate repetition
of that verse.

When some other phrase (than a verse) is repeated, the repeated part is to be put between 
`\lrep` and `\rrep` macros. If the repeat count is anything else than two, it will be
indicated by putting `\rep{3}` after the `\rrep` macro (replacing `3` with the actual
repeat count). If the span of the repeat is clear (for example exactly one line), `\rep{}`
macro can be used by itself.

Actual choruses i.e. verses that are jumped to more than once throughout the song can be
marked with `\beginchorus` or `\beginverse` (depending on their repeat behaviour), but each
lyrics line within them ought to be prefixed with `\chorusindent` macro, which indents the
line a bit. Elsewhere in the song, you can mark the spots from where to jump to chorus with
`\jumptochorus{Beginning words of the chorus}`.


#### Tags ####

Tags can be added to songs using a peculiar syntax (scripture reference system
of songs package is used for this purpose). All tags must be listed in file
`tags.can`. Define tags for a song by adding `tags=` keyval to `\beginsong` macro.
Note that a ` 1` must be appended to the tag name, like this
`\beginsong{Song name}[tags={love 1, smile 1}]`.

Tag index is found in the end of the result document.


Tentative TODO
--------------

*  Add more songs
*  Add chords for existing songs
*  Add translations and explanations for existing songs
*  Improve existing translations
*  Improve introduction for mantras (also other non-song texts)
*  Organize songs better and decide the categories (= chapters / parts)
*  Possibly add poems, prayers etc in between songs or in their own category(?)
*  Further develop visual style of the end document
