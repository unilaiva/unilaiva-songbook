    %% lp-include-tail.ly
    %% ==================
    %%
    %% This file should be included as the last thing within 'lilypond'
    %% environment, and creates a score with chord names, notes, vocals
    %% and guitar tabulature, in that order, if they have been defined.
    %%
    %% Requires that 'lp-include-head.ly' has been included before.
    %%
    %% See file 'lp-include-head.ly' for documentation.
    %%
    \score {
      <<
        \new ChordNames { \theChords }
        \new Staff { \clef "treble" \new Voice = "theVoice" { \theMelody } }
        \new Lyrics \lyricsto "theVoice" { \theLyricsOne }
        \new Lyrics \lyricsto "theVoice" { \theLyricsTwo }
        \new Lyrics \lyricsto "theVoice" { \theLyricsThree }
        \new Lyrics \lyricsto "theVoice" { \theLyricsFour }
        \new Lyrics \lyricsto "theVoice" { \theLyricsFive }
        \new Lyrics \lyricsto "theVoice" { \theLyricsSix }
        \new TabStaff { \clef "moderntab" \transpose c'' c \theMelody }
      >>
      \layout { }
    }
    \include "tex/lp-internal-midi-score.ly"
