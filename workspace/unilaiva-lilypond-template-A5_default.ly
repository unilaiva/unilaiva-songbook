% Unilaiva Songbook Lilypond template, default A5 version
% =======================================================
%
% Template for transcribing songs before adding them to the songbook. Can be
% used with a Lilypond editor, for example Frescobaldi.
%
% Instructions:
%
% 1. Copy this file to the *main directory* of the songbook project and name it
%    "WIP_<something>.ly". Files starting with WIP_ are ignored by git.
% 2. Open the "WIP_<something>.ly" file and do your transcribing there.
% 3. Add the song data between "BEGIN SONG DATA" and "END SONG DATA" comments
%    between the \include statements. Use theMelody, theLyrics{One, Two, ...}
%    and theChords variables.
% 3. When done, copy everything between "BEGIN SONG DATA" and "END SONG DATA"
%    within a song in the songbook. Uncomment the first line ("\begin{lily..."),
%    and the last two lines ("\include..." and "\end{lily...").
% 4. Done.
%

% BEGIN manually added stuff

    % This information is added when compiling unilaiva, and must be included
    % here for compatibility with the book.

    % Lilypond version is set in an included file, but must be explicitly
    % stated here in the beginning of the document to avoid an error.
    \version "2.22.1"

    #(set-default-paper-size "a5")
    \paper {
      % for default A5 booklets, the line-width property is as follows:
      line-width = 350\pt
      line-width = #(- line-width (* mm  3.000000) (* mm 1))
    }

% END manually added stuff



% BEGIN SONG DATA

%   \begin{lilywrap}\begin{lilypond}[]
    % transcribed by <person>, latest update on <yyyy-mm>
    \include "tex/lp-include-head.ly"
    theMelody = \relative c'' {
      \set melismaBusyProperties = #'() \slurDashed
      \key c \major \time 4/4 %\partial 4

    }
    theLyricsOne = \lyricmode {

    }
    theChords = \chordmode {

    }
    %\layout { #(layout-set-staff-size 15) } % for better fit
    %\include "tex/lp-include-tail-lyricsbelow.ly"
%   \end{lilypond}\end{lilywrap}

% END SONG DATA



% The following is grabbed from tex/lp-include-tail-lyricsbelow.ly and its child
% includes. They are here for easy changes, and for including the chords in the
% MIDI output when transcribing.

% BEGIN lp-include-tail-lyricsbelow.ly without the include

    \score {
      <<
        \new ChordNames { \theChords }
        \new Staff { \clef "treble" \new Voice = "theVoice" { \theMelody } }
        \new TabStaff { \clef "moderntab" \transpose c' c, \theMelody }
        \new Lyrics \lyricsto "theVoice" { \theLyricsOne }
        \new Lyrics \lyricsto "theVoice" { \theLyricsTwo }
        \new Lyrics \lyricsto "theVoice" { \theLyricsThree }
        \new Lyrics \lyricsto "theVoice" { \theLyricsFour }
        \new Lyrics \lyricsto "theVoice" { \theLyricsFive }
        \new Lyrics \lyricsto "theVoice" { \theLyricsSix }
        \new Lyrics \lyricsto "theVoice" { \theLyricsSeven }
        \new Lyrics \lyricsto "theVoice" { \theLyricsEight }
        \new Lyrics \lyricsto "theVoice" { \theLyricsNine }
        \new Lyrics \lyricsto "theVoice" { \theLyricsTen }
      >>
      \layout { }
    }

% END lp-include-tail-lyricsbelow.ly

% BEGIN lp-internal-midi.ly (with chords uncommented)

    \score { % for MIDI
      <<
        \unfoldRepeats \new Staff { % melody
          \set Staff.midiInstrument = #"acoustic guitar (nylon)"
          \set Staff.midiMinimumVolume = #0.7
          \set Staff.midiMaximumVolume = #0.9
          \transpose c' c, \theMelody
        }
        % % Chords, commented out for possible problems with repeats:
        % % not all songs have repeats used correctly in chords
        \unfoldRepeats \transpose c c, \new Staff {
          \set Staff.midiInstrument = #"acoustic guitar (nylon)"
          \set Staff.midiMinimumVolume = #0.5
          \set Staff.midiMaximumVolume = #0.7
          \theChords
        }
      >>
      \midi {
        \tempo 4 = 120
      }
    }

% END lp-internal-midi.ly
