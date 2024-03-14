    %% lp-include-head.ly
    %% ==================
    %%
    %% This file contains generic Lilypond settings and should be included
    %% as the first thing within the 'lilypond' environment.
    %%
    %% This is the version used for compact A5 booklets. For A4 booklets,
    %% include lp-include-head-spacious.ly instead.
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
    %% staffs. 'tex/lp-include-tail-notab-nolyrics' omits the lyrics and tabs,
    %% both.
    %%
    %% `lp-include-tail-multivoice-notab.ly` has support for two voices written
    %% on the same staff. The second voice is put into 'theMelodyTwo' variable.
    %% It might be reasonable to include '\voiceOne' instruction within
    %% 'theMelody', and '\voiceTwo' within theMelodyTwo.
    %%
    %% Melodies are supposed to be written one octave above the common female
    %% singing range (two octaves above the male one). This is taken into
    %% account for tabulature staff and MIDI. Tabs are by default transposed
    %% two octaves down, and for MIDI the main melody is transposed one octave
    %% down. Optional second voice is transposed two octaves down by default.
    %%

    % Includes the common settings
    \include "tex/lp-internal-common-head.ly"

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
      %annotate-spacing = ##t % for debugging spacing

      % system-system-spacing does not work in TeX documents; instead use
      % \newcommand{\betweenLilyPondSystem}[1]{\vspace*{.1ex}\linebreak}
      % in document preamble. Use star version of \vspace, if you want to
      % avoid page breaks.
      %system-system-spacing.padding = #1 % default: #1
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
          % Setup \sectionLabel style:
          \override SectionLabel
            .stencil = #(make-stencil-boxer 0.2 0.2 ly:text-interface::print)
          \override SectionLabel
            .color = #blue
          \override SectionLabel
            .font-size = #-1 % default: +1?
        }
      }
      \context {
        \ChordNames {
          % Setup vertical spacing:
          \override VerticalAxisGroup
            .staff-affinity = #DOWN
          \override VerticalAxisGroup
            .nonstaff-relatedstaff-spacing.padding = #0.3 % default: #0.5
          \override VerticalAxisGroup
            .nonstaff-unrelatedstaff-spacing.padding = #0.5 % default: #0.5
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
