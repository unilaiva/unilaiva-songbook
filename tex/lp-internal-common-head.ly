    % Lilypond version:
    \version "2.22.1"

    % Note names language; nederlands has: c sharp = cis, b flat = bes, b = b
    \language "nederlands"

    %%% Tunings for tablature, transposed to seem to have a compatible range
    %%% with guitar
    % Guitar in default tuning:
    ul-guitar-tuning = \stringTuning <e, a, d g b e'>
    % Soprano ukulele in high G tuning:
    ul-ukulele-tuning = \stringTuning \transpose c' c <g' c' e' a'>
    % Charango:
    ul-charango-tuning = \stringTuning \transpose c'' c <g' c'' e' a' e''>
    % Charango, but skip the middle E string pair, as it is ambiguous
    ul-charango-skipmiddle-tuning = \stringTuning \transpose c'' c <g' c'' e'''' a' e''>
    % This is the tuning used:
    ul-chosen-tuning = #ul-guitar-tuning

    \layout {
      \context {
        \TabStaff {
          \set TabStaff.stringTunings = #ul-chosen-tuning
        }
      }
    }

    % Modify chord name display for some chords
    chExceptionMusic = {
      <c e g d'>1-\markup { \super "add9" }      % usage example: g1:1.3.5.9
      <c e g b d'>1-\markup { \super "maj9" }    % usage example: g1:maj9
      <c e g a d'>1-\markup { \super "6(add9)" } % usage example: g1:6.9
    }
    % Convert music to list and prepend to existing exceptions.
    chExceptions = #(append
      (sequential-music-to-chord-exceptions chExceptionMusic #t)
      ignatzekExceptions)

    % Chord name color. This ought to be manually synced with 'chordcolor'
    % defined in file unilaiva-songbook_common.sty:
    color-chordnames = #(rgb-color 0.20 0 0.22)
    % The color used to signify alternative playing
    color-alt = #darkcyan

    \layout {
      \context {
        \ChordNames {
          \override ChordName.color = #color-chordnames
          % Display chord names only on changes and on new lines:
          \set chordChanges = ##t
        }
      }
      \context {
        \Voice \consists "Ambitus_engraver" % Shows vocal range
      }
    }

    % Draw a box around text and color it blue. Used by other functions.
    #(define-markup-command
      (blueboxed layout props text)
      (markup?)
      "Draw a box around text and color it blue."
      (interpret-markup layout props
        #{
          \markup {
            \with-color #darkblue
            \rounded-box{ #text }
          }
        #}
        )
      )

    % Draw the playout symbol. Used by other functions.
    #(define-markup-command
      (playoutsymbol layout props)
      ()
      "Draw the playout symbol"
      (interpret-markup layout props
        #{
          \markup {
            \with-color #darkgreen
            \fontsize #4 { \arrow-head #Y #DOWN ##t }
          }
        #}
        )
      )

    % Mark a spot in the music with a boxed blue text above the staff.
    % Use this to mark beginnings of musical sections. The text is given
    % as the only input parameter. Example: \sectionmark "2.A"
    sectionmark =
    #(define-event-function
      (parser location marktext)
      (markup?)
      "Mark the beginning of a musical section"
      #{
        ^\markup { \blueboxed{ #marktext } }
      #}
      )

    % Mark the playout start spot in the music. A symbol will be shown above
    % the staff. No parameters.
    pomark =
    #(define-event-function
      (parser location)
      ()
      "Mark the beginning of the playout"
      #{
        ^\markup { \playoutsymbol }
      #}
      )

    % Mark the playout start spot with a symbol followed by a boxed text used
    % to mark the beginning of a section. The text is given as the only input
    % parameter. Example: \posectionmark "2.B"
    posectionmark =
    #(define-event-function
      (parser location sectiontext)
      (markup?)
      "Mark the beginning of the playout and a musical section"
      #{
        ^\markup { \playoutsymbol \blueboxed{ #sectiontext } }
      #}
      )

    % Mark this spot above the staff with a text in generic style. The text
    % is given as the only input parameter. Example: \genmark "Yei!"
    genmark =
    #(define-event-function
      (parser location marktext)
      (markup?)
      "Make a generic text mark above the staff"
      #{
        ^\markup {
          \with-color #grey
          #marktext
        }
      #}
      )

    % Prints a Dal Segno (al fine) note. Should be paired with ^\segno somewhere.
    dalsegno = -\markup {
      \italic "D.S."
      \tiny \raise #1
      \musicglyph #"scripts.segno"
    }

    % Prints a Da Capo (al fine) note.
    dacapo = -\markup {
      \italic "D.C."
    }

    % Mark the spot of the preceding note with textual alternative playing
    % instruction above the staff (for example verse number). Can be paired
    % with \altnote *before* the note in question.
    altmark =
    #(define-event-function
      (parser location marktext)
      (markup?)
      "Make textual mark to signify alternative play instructions"
      #{
        ^\markup {
          \with-color #color-alt
          \italic #marktext
        }
      #}
      )

    % Setup the following note or lyric token's color to #color-alt. Use this
    % to mark a note to be of different color to signify alternative playing.
    % To explain this, use \altmark function *after* the note. To colorize only
    % one note head in a beam with multiple heads, state \single immediately
    % before \altcol.
    altcol = {
      \once\override NoteHead.color = #color-alt
      \once\override Stem.color = #color-alt
      \once\override Accidental.color = #color-alt
      \once\override Flag.color = #color-alt
      \once\override Dots.color = #color-alt 
      \once\override TabNoteHead.color = #color-alt
      \once\override Slur.color = #color-alt
      \once\override LyricText.color = #color-alt
      % %% KEEP THIS COMMENTED %% \once\override Beam.color = #color-alt
    }

    % Defines some variables as empty, so that if the user doesn't define them,
    % nothing breaks and they will just be ignored.
    theMelodyTwo = {}
    theChords = \chordmode {}
    theLyricsOne = \lyricmode {}
    theLyricsTwo = \lyricmode {}
    theLyricsThree = \lyricmode {}
    theLyricsFour = \lyricmode {}
    theLyricsFive = \lyricmode {}
    theLyricsSix = \lyricmode {}
    theLyricsSeven = \lyricmode {}
    theLyricsEight = \lyricmode {}
    theLyricsNine = \lyricmode {}
    theLyricsTen = \lyricmode {}
