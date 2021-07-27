    %% lilypond-settings-include.ly
    %% ============================
    %%
    %% This file holds songbookwide settings for lilypond snippets, so that they
    %% all appear the same. The file is to be included as the first thing in the
    %% lilypond environment like this:
    %%
    %%   \begin{lilypond}[]
    %%     \include "tex/lilypond-settings-include.ly"
    %%     % all the lilypond code
    %%   \end{lilypond}

    % Sets the global staff size, it scales everything. Recommended size is 18.
    % With Noto fonts, 17 might be better.
    #(set-global-staff-size 18)

    \paper {
      %% This sets up custom fonts. They must be loaded in the LaTeX document
      %% as packages(?). See fonts available to lilypond with command
      %% 'lilypond -dshow-available-fonts x', though it doesn't show which
      %% are installed in the document.
      %% See: https://lilypond.org/doc/v2.20/Documentation/notation/fonts#entire-document-fonts
      %% Commented out for now as it multiplies compile time, using defaults.
%       #(define fonts
%         (set-global-fonts
%           #:roman "NotoSans-ExtraCondensedMedium"
%           #:sans "NotoSans-ExtraCondensedMedium"
%           #:factor (/ staff-height pt 20)
%                    ))

      indent = #0
      ragged-right = ##f
      ragged-last = ##f
      ragged-bottom = ##f
    }

    \layout {
      \context {
        \ChordNames {
          % Chord name color. This ought to be manually synced with 'chordcolor'
          % defined in file unilaiva-songbook_common.sty:
          \override ChordName.color = #(rgb-color 0.3 0 0.4)
          % Display chord names only on changes and on new lines:
          \set chordChanges = ##t
        }
      }
    }
