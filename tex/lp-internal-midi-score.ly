    \score { % for MIDI
      <<
        \unfoldRepeats \new Staff { % melody
          \set Staff.midiInstrument = #"acoustic guitar (nylon)"
          \transpose c'' c \theMelody
        }
        %% Chords, commented out for possible problems with repeats
        %\unfoldRepeats \new Staff {
        %  \set Staff.midiInstrument = #"acoustic grand"
        %  \theChords
        %}
      >>
      \midi {
        \tempo 4 = 120
      }
    }
