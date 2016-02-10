wisdom-songbook
===============

wisdom-songbook is a collection of song lyrics etc for the contributors' 
private use. 


Environment
-----------

wisdom-songbook is a project written in LaTeX. You must have LaTeX with
`pdflatex` command and some standard packages installed on your system.

Our project requires only some pretty standard LaTeX packages, which 
are included in many LaTeX installations by default, to be installed on 
the system. They are all included with `\usepackage` commands in the 
beginning of the project's main file: `wisdom-songbook.tex`.

One of the package dependencies, `songs`, is included in the project
tree and used instead of a one possibly installed on the system. This 
is because of compatibility reasons to ensure a certain version: the 
package is used heavily and some of its commands are redefined.

The `songs` package uses two binaries to create song indexes. These must
be manually compiled from the source in `ext_packages/src` and placed
into `ext_packages/bin/`. If the binaries are missing, the producing
of the document works otherwise, but song indexes will be missing.

# Compiling `songs` binaries on UNIX #

This requires only basic compiling tools: `make` and `gcc` which are
most likely already installed on your system. 

Go to the base directory of our project and execute the following commands:

        cd ext_packages/src
        tar xvzf songs-2.18.tar.gz
        cd songs-2.18
        COMPILEBASEDIR=$(pwd)
        ./configure
        make   # don't worry if there are some errors
        make install prefix="$COMPILEBASEDIR/tmpinstall"
        mkdir ../../bin
        cp tmpinstall/bin/* ../../bin/
        cd ..
        rm -R songs-2.18
        
Recommended way to build a PDF document out of our project is to use
`pdflatex`. You may use the provided `compile_wisdom.sh` shell script
to do the build: it calls `pdflatex` and also builds indexes with the
`songs` package binaries (if they exist).


Project structure and guidelines
--------------------------------

Project's main file is `wisdom-songbook.tex`. It includes all the
other files in the project and contains configuration.

Long `\renewcommand`s ought to be put into `wisdom-songbook-extra.tex` to
maintain readability of the main file.

Song data and other *content* will be in various files inside `songdata`
subdirectory and will be inputed into the main file.

External packages (`songs` for now) are in `ext_packages` subdirectory.

Lines ought to be less than 100 characters long (is anyone using 80 column
terminals still?).

See `songs` package documentation in [http://songs.sourceforge.net/songsdoc/songs.html](http://songs.sourceforge.net/songsdoc/songs.html).

Stuff inside `songs` environment (the files in `songdata` directory) ought
to contain only individual songs (and data related to them) between
`\beginsong` and `\endsong` tags plus other data wrapped in `intersong`
environment. 

Use `\sclearpage` to jump to the beginning of a new page and `\scleardpage` to
hop to the beginning of a new left-side page. Suggest a good page brake spot
with `\brk`.
