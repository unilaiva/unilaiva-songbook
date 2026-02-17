    %% lp-include-tail-multivoice-notab.ly
    %% ===================================
    %%
    %% This file should be included as the last thing within 'lilypond'
    %% environment, and creates a score with chord names, notes with
    %% two voices, and lyrics, in that order, if they have been defined.
    %%
    %% In the songs using this, specify \voiceOne and \voiceTwo within
    %% \theMelodyOne and \theMeldodyTwo to set stem direction.
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
        \new Staff <<
          \clef "treble"
          \new Voice = "theVoice" { \theMelody }
          \new Voice = "theVoiceTwo" { \theMelodyTwo }
        >>
        \include "tex/lp-internal-scorepart-lyrics.ly"
      >>
      \layout { }
    }
    \include "tex/lp-internal-score-midi.ly"
