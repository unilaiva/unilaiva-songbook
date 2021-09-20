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

    % Note names language; nederlands has: c sharp = cis, b flat = bes, b = b
    \language "nederlands"

    % Sets the global staff size, it scales everything. Recommended size is 18,
    % but we use 16 for space reasons. With Noto fonts, 15 might be needed.
    #(set-global-staff-size 16)

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
      system-system-spacing.padding = #1.3 % default: #1
      %annotate-spacing = ##t % for debugging spacing
    }

    % About vertical spacing: https://lilypond.org/doc/v2.22/Documentation/notation/flexible-vertical-spacing-within-systems#spacing-of-non_002dstaff-lines
    \layout {
      \context {
        \Score {
          % Setup vertical spacing:
          \override VerticalAxisGroup
            .default-staff-staff-spacing.padding = #1 % default: #2?
          \override VerticalAxisGroup
            .default-staff-staff-spacing.basic-distance = #5 % default: #10?
          \override VerticalAxisGroup
            .default-staff-staff-spacing.minimum-distance = #5 % default: #10?
        }
      }
      \context {
        \ChordNames {
          % Chord name color. This ought to be manually synced with 'chordcolor'
          % defined in file unilaiva-songbook_common.sty:
          \override ChordName.color = #(rgb-color 0.18 0 0.24)
          % Display chord names only on changes and on new lines:
          \set chordChanges = ##t
          % Setup vertical spacing:
          \override VerticalAxisGroup
            .staff-affinity = #DOWN
          \override VerticalAxisGroup
            .nonstaff-relatedstaff-spacing.padding = #0.3 % default: #0.5
        }
      }
      \context {
        \Lyrics {
          % Setup vertical spacing:
          \override VerticalAxisGroup
            .staff-affinity = #UP
          \override VerticalAxisGroup
            .nonstaff-relatedstaff-spacing.padding = #0.5 % default: #0.5
          \override VerticalAxisGroup
            .nonstaff-nonstaff-spacing.padding = #0.3 % default: #0.5
          \override VerticalAxisGroup
            .nonstaff-nonstaff-spacing.minimum-distance = #0.3 % default: #0.5
          \override VerticalAxisGroup
            .nonstaff-unrelatedstaff-spacing.padding = #0.5 % default: #1.5
        }
      }
    }

    % Draw a box around text and color it blue. Used by other functions.
    #(define-markup-command
      (blueboxed layout props text)
      (markup?)
      "Draw a box around text and color it blue."
      (interpret-markup layout props
        #{
          \markup {
            \with-color #darkblue
            \rounded-box{ #text }
          }
        #}
      )
    )

    % Draw the playout symbol. Used by other functions.
    #(define-markup-command
      (playoutsymbol layout props)
      ()
      "Draw the playout symbol"
      (interpret-markup layout props
        #{
          \markup {
            \with-color #darkgreen
            \fontsize #4 { \arrow-head #Y #DOWN ##t }
          }
        #}
      )
    )

    % Mark a spot in the music with a boxed blue text above the staff.
    % Use this to mark beginnings of musical sections. The text is given
    % as the only input parameter. Example: \sectionmark "2.A"
    sectionmark =
    #(define-event-function
      (parser location marktext)
      (markup?)
      "Mark the beginning of a musical section"
      #{
        ^\markup { \blueboxed{ #marktext } }
      #}
    )

    % Mark the playout start spot in the music. A symbol will be shown above
    % the staff. No parameters.
    pomark =
    #(define-event-function
      (parser location)
      ()
      "Mark the beginning of the playout"
      #{
        ^\markup { \playoutsymbol }
      #}
    )

    % Mark the playout start spot with a symbol followed by a boxed text used
    % to mark the beginning of a section. The text is given as the only input
    % parameter. Example: \posectionmark "2.B"
    posectionmark =
    #(define-event-function
      (parser location sectiontext)
      (markup?)
      "Mark the beginning of the playout and a musical section"
      #{
        ^\markup { \playoutsymbol \blueboxed{ #sectiontext } }
      #}
    )

    % Mark a spot in the music with a cyan text above the staff.
    % The text is given as the only input parameter. Example: \genmark "(3.)"
    genmark =
    #(define-event-function
      (parser location marktext)
      (markup?)
      "Mark the beginning of a musical section"
      #{
        ^\markup {
          \with-color #darkcyan
          #marktext
        }
      #}
    )

    % Defines some variables as empty, so that if the user doesn't define them,
    % nothing breaks and they will just be ignored.
    theChords = \chordmode {}
    theLyricsOne = \lyricmode {}
    theLyricsTwo = \lyricmode {}
    theLyricsThree = \lyricmode {}
    theLyricsFour = \lyricmode {}
    theLyricsFive = \lyricmode {}
    theLyricsSix = \lyricmode {}
    theLyricsSeven = \lyricmode {}
