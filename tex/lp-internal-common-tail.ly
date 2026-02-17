    % Apply optional size override for this snippet, then clear it
    #(when myStaffSize
      (set-global-staff-size myStaffSize)
      (set! myStaffSize #f))

    % Define fonts (must be done here in the tail include after a possible
    % call to \setStaffSize).
    \paper {
      #(define fonts
        (set-global-fonts
          #:roman "Noto Sans Medium"
          #:sans "Noto Sans Medium"
          #:typewriter "Noto Sans Mono Medium"
          #:factor (/ staff-height pt 22)
        ))
    }

%     %% For upcoming lilypond 2.25 global fonts can be set in the following way,
%     %% and it can be done in the head include, as setting staff size will not
%     %% reset fonts setup like this. (What about factor?)
%     \paper {
%       property-defaults.fonts.serif = "Noto Sans Medium"
%       property-defaults.fonts.sans = "Noto Sans Medium"
%       property-defaults.fonts.typewriter = "Noto Sans Mono Medium"
%     }

    % Set vars for reuse (this can't be used in set-global-fonts)
    #(define fontRegular "Noto Sans Medium")
    #(define fontBold "Noto Sans Bold")
    #(define fontMonoRegular "Noto Sans Mono Medium")
    #(define fontMonoBold "Noto Sans Mono Bold")

    \layout {
      \context {
        \ChordNames {
          \override ChordName.font-name = #fontBold
          \override ChordName.font-size = #-0.2
        }
      }
      \context {
        \TabStaff {
          \override Clef.font-name = #fontBold
          \override TabNoteHead.font-name = #fontBold
        }
      }
      \context {
        \Lyrics {
          \override StanzaNumber.font-name = #fontBold
          \override LyricText.font-size = #-0.2
          %\override StanzaNumber.font-size = #-0.2
        }
      }
    }
