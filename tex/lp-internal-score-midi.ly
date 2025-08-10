    \score { % for MIDI
      <<
        \unfoldRepeats \new Staff { % melody
          \set Staff.midiInstrument = #"flute"
          \set Staff.midiMinimumVolume = #0.6
          \set Staff.midiMaximumVolume = #0.9
          % Transposed down one octave to the common female singing range
          \transpose c c, \theMelody
        }
        \unfoldRepeats \new Staff { % melody, 2nd voice
          \set Staff.midiInstrument = #"accordion"
          \set Staff.midiMinimumVolume = #0.5
          \set Staff.midiMaximumVolume = #0.8
          % Transposed down two octaves to the common male singing range
          \transpose c c,, \theMelodyTwo
        }
        % % Chords, commented out for possible problems with repeats:
        % % not all songs have repeats used correctly in chords
        % \unfoldRepeats \new Staff {
        %   \set Staff.midiInstrument = #"acoustic guitar (nylon)"
        %   \set Staff.midiMinimumVolume = #0.4
        %   \set Staff.midiMaximumVolume = #0.7
        %   % Transposed down two octaves to the guitar open chord range
        %   \transpose c c,, \theChords
        % }
      >>
      \midi {
        \tempo 4 = 120
      }
    }
