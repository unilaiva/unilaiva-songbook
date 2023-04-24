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
        % \unfoldRepeats \transpose c c, \new Staff {
        %   \set Staff.midiInstrument = #"acoustic guitar (nylon)"
        %   \set Staff.midiMinimumVolume = #0.5
        %   \set Staff.midiMaximumVolume = #0.7
        %   \theChords
        % }
      >>
      \midi {
        \tempo 4 = 120
      }
    }
