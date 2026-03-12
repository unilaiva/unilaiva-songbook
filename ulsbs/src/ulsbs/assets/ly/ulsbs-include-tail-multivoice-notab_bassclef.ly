    % SPDX-FileCopyrightText: 2016-2026 Lari Natri <lari.natri@iki.fi>
    % SPDX-License-Identifier: GPL-3.0-or-later
    % LilyPond tail include: two voices, bass clef, no TAB.
    % This file is part of the 'ulsbs' package.

    %% ulsbs-include-tail-multivoice-notab_bassclef.ly
    %% ============================================
    %%
    %% Bass clef version.
    %%
    %% This file should be included as the last thing within 'lilypond'
    %% environment, and creates a score with chord names, notes with
    %% two voices, and lyrics, in that order, if they have been defined.
    %%
    %% In the songs using this, specify \voiceOne and \voiceTwo within
    %% \theMelodyOne and \theMeldodyTwo to set stem direction.
    %%
    %% Requires that 'ulsbs-include-head.ly' has been included before.
    %%
    %% See file 'ulsbs-include-head.ly' for documentation.
    %%
    \include "ulsbs-internal-common-tail.ly"
    \score {
      <<
        \new ChordNames {
          % Use chord name modifications defined in ulsbs-internal-common-head.ly
          \set chordNameExceptions = #chExceptions
          \theChords
        }
        \new Staff <<
          \clef "bass"
          \new Voice = "theVoice" { \transpose c c,, \theMelody }
          \new Voice = "theVoiceTwo" { \transpose c c,, \theMelodyTwo }
        >>
        \include "ulsbs-internal-scorepart-lyrics.ly"
      >>
      \layout { }
    }
    \include "ulsbs-internal-score-midi.ly"
