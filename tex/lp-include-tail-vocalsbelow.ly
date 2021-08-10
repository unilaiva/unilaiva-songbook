    %% lp-include-tai-vocalsbelow.ly
    %% =============================
    %%
    %% This file should be included as the last thing within 'lilypond'
    %% environment, and creates a score with chord names, notes, guitar
    %% tabulature and vocals, in that order, if they have been defined.
    %%
    %% Requires that 'lp-include-head.ly' has been included before.
    %%
    %% See file 'lp-include-head.ly' for documentation.
    %%
    \score {
      <<
        \new ChordNames { \theChords }
        \new Staff { \clef "treble" \new Voice = "theVoice" { \theMelody } }
        \new TabStaff { \clef "moderntab" \transpose c'' c \theMelody }
        \new Lyrics \lyricsto "theVoice" { \theLyricsOne }
        \new Lyrics \lyricsto "theVoice" { \theLyricsTwo }
        \new Lyrics \lyricsto "theVoice" { \theLyricsThree }
        \new Lyrics \lyricsto "theVoice" { \theLyricsFour }
        \new Lyrics \lyricsto "theVoice" { \theLyricsFive }
        \new Lyrics \lyricsto "theVoice" { \theLyricsSix }
      >>
      \layout { }
    }
    \include "tex/lp-internal-midi-score.ly"
  }
