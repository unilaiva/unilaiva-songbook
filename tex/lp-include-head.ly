    %% lp-include-head.ly
    %% ==================
    %%
    %% This file contains generic Lilypond settings and should be included
    %% as the first thing within the 'lilypond' environment.
    %%
    %% To make notation as easy as possible, one should after this include
    %% define the variable 'theMelody' that contains the melody notes (and
    %% optionally 'theChords' and 'theLyricsOne' ... 'theLyricsSix'), and
    %% finally, as the last thing in the 'lilypond' environment, include
    %% the file 'lp-include-tail.ly'.
    %%
    %% Here is a full example on how to embed lilypond in Unilaiva songbooks:
    %%
    %% \begin{lilywrap}\begin{lilypond}[] \include "tex/lp-include-head.ly"
    %%   theMelody = \relative c'' { | c4 e4 d4 f4 | c1 }
    %%   theLyricsOne = \lyricmode { | I am full of | joy}
    %%   theChords = \chordmode { c2 d2:m | c1 }
    %%   \include "tex/lp-include-tail.ly"
    %% \end{lilypond}\end{lilywrap}
    %%
    %% Note that if 'theChords' or 'theLyricsOne' is omitted, chords and lyrics
    %% will be ignored. If file 'tex/lp-include-tail.ly' is replaced with
    %% 'tex/lp-include-tail-notab.ly', no guitar tabulature is created. Or if
    %% it is replaced with 'tex/lp-include-tail-lyricsbelow.ly', the lyrics will
    %% be laid below the tabulature staff instead of between normal and tab
    %% staffs.
    %%
    %% Note that tabulature is transposed two octaves down!
    %%

    % Lilypond version:
    \version "2.22.0"

    % Sets the global staff size, it scales everything. Recommended size is 18,
    % but we use 17 for space reasons. With Noto fonts, 16 might be needed.
    #(set-global-staff-size 17)

    \paper {
      %% This sets up custom fonts. They must be loaded in the LaTeX document
      %% as packages(?). See fonts available to lilypond with command
      %% 'lilypond -dshow-available-fonts x', though it doesn't show which
      %% are installed in the document.
      %% See: https://lilypond.org/doc/v2.20/Documentation/notation/fonts#entire-document-fonts
      %% Commented out for now as it multiplies compile time, using defaults.
%       #(define fonts
%         (set-global-fonts
%           #:roman "NotoSans-ExtraCondensedMedium"
%           #:sans "NotoSans-ExtraCondensedMedium"
%           #:factor (/ staff-height pt 20)
%                    ))

      indent = #0
      ragged-right = ##f
      ragged-last = ##f
      ragged-bottom = ##f
    }

    \layout {
      \context {
        \ChordNames {
          % Chord name color. This ought to be manually synced with 'chordcolor'
          % defined in file unilaiva-songbook_common.sty:
          \override ChordName.color = #(rgb-color 0.3 0 0.4)
          % Display chord names only on changes and on new lines:
          \set chordChanges = ##t
        }
      }
    }

    % Mark a spot with text above the staff. Text is given as the only
    % parameter. Example: \genmark "my text"
    genmark =
    #(define-music-function
      (parser location marktext)
      (markup?)
      #{
        ^\markup{
          \with-color #darkblue
          \rounded-box{ #marktext }
        }
      #})

    % Mark a spot where the playout ought to start at. A symbol will be
    % shown above the staff. No parameters.
    pomark =
    #(define-music-function
      (parser location)
      ()
      #{
        ^\markup{
          \fontsize #6 {
            \with-color #darkgreen
            \arrow-head #Y #DOWN ##t
          }
        }
      #})

    % Defines some variables as empty, so that if the user doesn't define them,
    % nothing breaks and they will just be ignored.
    theChords = \chordmode {}
    theLyricsOne = \lyricmode {}
    theLyricsTwo = \lyricmode {}
    theLyricsThree = \lyricmode {}
    theLyricsFour = \lyricmode {}
    theLyricsFive = \lyricmode {}
    theLyricsSix = \lyricmode {}
