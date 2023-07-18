    %% lp-include-tail-notab-nolyrics.ly
    %% =================================
    %%
    %% This file should be included as the last thing within 'lilypond'
    %% environment, and creates a score with chord names, notes and
    %% lyrics, in that order, if they have been defined.
    %%
    %% Requires that 'lp-include-head.ly' has been included before.
    %%
    %% See file 'lp-include-head.ly' for documentation.
    %%
    \score {
      <<
        \new ChordNames { \theChords }
        \new Staff { \clef "treble" \new Voice = "theVoice" { \theMelody } }
      >>
      \layout { }
    }
    \include "tex/lp-internal-midi-score.ly"
