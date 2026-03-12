    % SPDX-FileCopyrightText: 2016-2026 Lari Natri <lari.natri@iki.fi>
    % SPDX-License-Identifier: GPL-3.0-or-later
    % LilyPond include: spacious header settings for A4.
    % This file is part of the 'ulsbs' package.

    %% ulsbs-include-head-spacious.ly
    %% ===========================
    %%
    %% This file contains generic Lilypond settings and should be included
    %% as the first thing within the 'lilypond' environment.
    %%
    %% This is the version meant to be used for spacious engravings on A4 paper.
    %% For compact A5 booklets, include ulsbs-include-head-spacious.ly instead.
    %%
    %% To make notation as easy as possible, one should after this include
    %% define the variable 'theMelody' that contains the melody notes (and
    %% optionally 'theChords' and 'theLyricsOne' ... 'theLyricsSix'), and
    %% finally, as the last thing in the 'lilypond' environment, include
    %% the file 'ulsbs-include-tail.ly'.
    %%
    %% Here is a full example on how to embed lilypond in Unilaiva songbooks:
    %%
    %% \begin{lilywrap}\begin{lilypond}[] \include "ulsbs-include-head.ly"
    %%   theMelody = \relative c'' { | c4 e4 d4 f4 | c1 }
    %%   theLyricsOne = \lyricmode { | I am full of | joy}
    %%   theChords = \chordmode { c2 d2:m | c1 }
    %%   \include "ulsbs-include-tail.ly"
    %% \end{lilypond}\end{lilywrap}
    %%
    %% Note that if 'theChords' or 'theLyricsOne' is omitted, chords and lyrics
    %% will be ignored. If file 'input{ulsbs-include-tail.ly' is replaced with
    %% 'input{ulsbs-include-tail-notab.ly', no guitar tabulature is created. Or if
    %% it is replaced with 'input{ulsbs-include-tail-lyricsbelow.ly', the lyrics will
    %% be laid below the tabulature staff instead of between normal and tab
    %% staffs.
    %%
    %% Note that tabulature is transposed two octaves down!
    %%

    % Includes the common settings
    \include "ulsbs-internal-common-head.ly"

    % Sets the global staff size, it scales everything. Recommended size is 18.
    #(set-global-staff-size 18)

    \paper {
      indent = #0
      ragged-right = ##f
      ragged-last = ##f
      ragged-bottom = ##f
      %annotate-spacing = ##t % for debugging spacing

      % system-system-spacing does not work in TeX documents; instead use
      % \newcommand{\betweenLilyPondSystem}[1]{\vspace*{.5ex}\linebreak}
      % in document preamble. Use star version of \vspace, if you want to
      % avoid page breaks.
      %system-system-spacing.padding = #1 % default: #1
    }

    % About vertical spacing: https://lilypond.org/doc/v2.24/Documentation/notation/flexible-vertical-spacing-within-systems#spacing-of-non_002dstaff-lines
    \layout {
      \context {
        \Score {
          % Setup vertical spacing:
          \override VerticalAxisGroup
            .default-staff-staff-spacing.padding = #2 % default: #2?
          \override VerticalAxisGroup
            .default-staff-staff-spacing.basic-distance = #10 % default: #10?
          \override VerticalAxisGroup
            .default-staff-staff-spacing.minimum-distance = #10 % default: #10?
        }
      }
      \context {
        \ChordNames {
          % Setup vertical spacing:
          \override VerticalAxisGroup
            .staff-affinity = #DOWN
          \override VerticalAxisGroup
            .nonstaff-relatedstaff-spacing.padding = #0.5 % default: #0.5
          \override VerticalAxisGroup
            .nonstaff-unrelatedstaff-spacing.padding = #1.5 % default: #0.5
        }
      }
      \context {
        \Lyrics {
          % Setup vertical spacing:
          \override VerticalAxisGroup
            .staff-affinity = #CENTER
          \override VerticalAxisGroup
            .nonstaff-nonstaff-spacing.basic-distance = #2.1 % default: #2.0
          \override VerticalAxisGroup
            .nonstaff-nonstaff-spacing.minimum-distance = #2.1 % default: #0.0?
            \override VerticalAxisGroup
            .nonstaff-nonstaff-spacing.padding = #0.5 % default: #0.5
          \override VerticalAxisGroup
            .nonstaff-relatedstaff-spacing.padding = #0.5 % default: #0.5
          \override VerticalAxisGroup
            .nonstaff-unrelatedstaff-spacing.padding = #1.5 % default: #1.5
        }
      }
    }
