% SPDX-FileCopyrightText: 2016-2026 Lari Natri <lari.natri@iki.fi>
% SPDX-License-Identifier: GPL-3.0-or-later
% Default songbook class config for main Unilaiva Songbook.
% This file is part of the 'ulsbs' package.

\NeedsTeXFormat{LaTeX2e}
\ProvidesClass{ulsbs-songbook-unilaiva-default}[2026/03/04 v1.0]

\RequirePackage{kvoptions}

% Child-only key=val options
\SetupKeyvalOptions{family=ulsbs-child,prefix=ulsbschild@}
%\DeclareStringOption[teal]{accent} % new child option with default (example)

% Forward any user option (including key=val) to the base class
\DeclareOption*{\PassOptionsToClass{\CurrentOption}{ulsbs-songbook}}

% Set child defaults for parent's kvoptions keys (user options will override)
% IMPORTANT: avoid passing comma-containing values (like keywords) via class options;
% instead set such values after loading the parent (e.g., redefine \ulBookKeywords).
\PassOptionsToClass{
  paper={a5paper},
  maintitle={Unilaiva Songbook},
  motto={paths to deeper experiencing},
  wwwlink={https://unilaiva.aavalla.net/},
  wwwqr={QR_https_unilaiva_aavalla_net.png},
  author={Lari Natri},
  subject={Songbook},
  keywords={songbook, songs, spiritual, entheogens, ceremony, folk songs}
}{ulsbs-songbook}

% NOTE: QR image created with:
%       qrencode -s 32 -l Q -o content/img/QR_https_unilaiva_aavalla_net.png "https://unilaiva.aavalla.net/"
%       --> then added the Unilaiva icon in the middle as 320x320 image with borders


% Handle size/side: force 10pt,twoside; accept them silently; ignore conflicts
\DeclareOption{10pt}{}
\DeclareOption{11pt}{\ClassWarning{ulsbs-songbook-unilaiva-default}{Ignoring 11pt; forcing 10pt}}
\DeclareOption{12pt}{\ClassWarning{ulsbs-songbook-unilaiva-default}{Ignoring 12pt; forcing 10pt}}

% Allow setting font size, but warn if other than 10pt
\newif\iful@fontsizespecified
\ul@fontsizespecifiedfalse
\DeclareOption{10pt}{%
  \PassOptionsToClass{10pt}{ulsbs-songbook}%
  \ul@fontsizespecifiedtrue%
}
\DeclareOption{11pt}{%
  \PassOptionsToClass{11pt}{ulsbs-songbook}%
  \ul@fontsizespecifiedtrue%
  \ClassWarning{ulsbs-songbook-unilaiva-default}{Font size 10pt is recommended, but 11pt is used}%
}
\DeclareOption{12pt}{%
  \PassOptionsToClass{12pt}{ulsbs-songbook}%
  \ul@fontsizespecifiedtrue%
  \ClassWarning{ulsbs-songbook-unilaiva-default}{Font size 10pt is recommended, but 12pt is used}%
}

% Handle side: twoside; accept it silently; ignore conflicts
\DeclareOption{oneside}{\ClassWarning{ulsbs-songbook-unilaiva-default}{Ignoring oneside; forcing twoside}}
\DeclareOption{twoside}{}

% Process child keys first, then forward the rest
\ProcessKeyvalOptions*
\ProcessOptions\relax


% LOAD THE PARENT CLASS

\iful@fontsizespecified
  \LoadClass[twoside,openright,onecolumn]{ulsbs-songbook}
\else % default to 10pt
  \LoadClass[10pt,twoside,openright,onecolumn]{ulsbs-songbook}
\fi


\renewcommand{\ulImprintPageFootnote}{%
  The material in this book is collected and transcribed, with help from a
  multitude of people, from various audio and text sources --- and through
  singing, playing, dancing, sharing, listening, studying and learning.
  This is a work in progress, made with Love and the feeling of immense Gratitude
  towards these beautiful songs, the people who created them, and the
  amazing Mystery of the Universe.
}

% Setup the mark at song end, just above the horizontal line that ends a song;
% if this macro is empty (the default), only the line is displayed.
\renewcommand{\ulSongEndMark}{%
  \color{gray}\symboliifont ◼%
}

% Smaller melody notes
\renewcommand{\mnsymbolstyle}{\microsize}

% Do not display language *code* for EN
\renewcommand{\passageomitlangcodes}{EN}
\renewcommand{\explanationomitlangcodes}{EN}

\showphtrue
\showphintoctrue
\showkeytrue
\showgoodkeystrue
\showtranslationtrue
\showofftrue
\showextrue
\showtagstrue
\shownotestrue
\showbeatstrue
\showauthtrue
\showlilypondtrue
\showexplanationtrue
\showtranslationtrue
\showfeelertrue
\showaltchordstrue
