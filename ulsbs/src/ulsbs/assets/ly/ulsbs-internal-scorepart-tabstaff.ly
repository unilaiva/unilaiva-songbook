        % SPDX-FileCopyrightText: 2016-2026 Lari Natri <lari.natri@iki.fi>
        % SPDX-License-Identifier: GPL-3.0-or-later
        %
        % LilyPond score part: TAB staff for melody.
        % This file is part of the 'ulsbs' package.

        % TAB staff to be inserted into a score
        % Transposed down two octaves to the common male singing range
        \new TabStaff { \clef "moderntab" \transpose c c,, \theMelody }
        %% TAB staff for the second voice, commented out
        %\new TabStaff { \clef "moderntab" \transpose c c,, \theMelodyTwo }
