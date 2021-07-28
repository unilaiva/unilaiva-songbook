    %% lilypond-score-chords-melody-tabs.ly
    %% ====================================
    %%
    %% This file holds the default score construction for Lilypond snippets,
    %% where you want chords, melody, lyrics and tabs displayed in a default
    %% way.
    %%
    %% Note that guitar tabs will be transposed two octaves down from the
    %% melody. So the lowest possible melody note is e', the e below middle c.
    %%
    %% This file should be included in 'lilypond' environment after definition
    %% of the required variables theMelody, theLyricsOne and theChords for
    %% example like this:
    %%
    %% \begin{lilywrap}\begin{lilypond}[] \include "tex/lilypond-settings-include.ly"
    %%   theMelody = \relative c'' { | c4 e4 d4 f4 | c1 }
    %%   theLyricsOne = \lyricmode { | I am full of | joy}
    %%   theChords = \chordmode { c2 d2:m | c1 }
    %%   \include "tex/lilypond-score-chords-melody-tabs.ly"
    %% \end{lilypond}\end{lilywrap}
    %%
    \score {
      <<
        \new ChordNames { \theChords }
        \new Staff { \clef "treble" \new Voice = "theVoice" { \theMelody } }
        \new Lyrics = "lyricsOne" \lyricsto "theVoice" \theLyricsOne
        \new TabStaff { \clef "moderntab" \transpose c'' c \theMelody }
      >>
    }
