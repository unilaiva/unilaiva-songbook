    %% lp-include-tail_bassclef.ly
    %% ===========================
    %%
    %% Bass clef version.
    %%
    %% This file should be included as the last thing within 'lilypond'
    %% environment, and creates a score with chord names, notes, guitar
    %% tabulature and lyrics, in that order, if they have been defined.
    %%
    %% Requires that 'lp-include-head.ly' has been included before.
    %%
    %% See file 'lp-include-head.ly' for documentation.
    %%
    \include "tex/lp-internal-common-tail.ly"
    \score {
      <<
        \new ChordNames {
          % Use chord name modifications defined in lp-internal-common-head.ly
          \set chordNameExceptions = #chExceptions
          \theChords
        }
        \new Staff {
          \clef "bass"
          \new Voice = "theVoice" { \transpose c c,, \theMelody }
        }
        %\include "tex/lp-internal-scorepart-tabstaff.ly"
        \include "tex/lp-internal-scorepart-lyrics.ly"
      >>
      \layout { }
    }
    \include "tex/lp-internal-score-midi.ly"
