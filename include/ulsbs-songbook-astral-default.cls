% SPDX-FileCopyrightText: 2016-2026 Lari Natri <lari.natri@iki.fi>
% SPDX-License-Identifier: GPL-3.0-or-later
% Default songbook class config for Astral books.
% This file is part of the 'ulsbs' package.

\NeedsTeXFormat{LaTeX2e}
\ProvidesClass{ulsbs-songbook-astral-default}[2026/03/04 v1.0]

\RequirePackage{kvoptions}

% Child-only key=val options
\SetupKeyvalOptions{family=ulsbs-child,prefix=ulsbschild@}
%\DeclareStringOption[teal]{accent} % new child option with default (example)

% Forward any user option (including key=val) to the base class
\DeclareOption*{\PassOptionsToClass{\CurrentOption}{ulsbs-songbook}}

% Set child defaults for parent's kvoptions keys (user options will override)
% IMPORTANT: avoid passing comma-containing values (like keywords) via class options;
% instead set such values after loading the parent (e.g., redefine \pdfkeywords).
\PassOptionsToClass{
  paper={a5paper},
  maintitle={Unilaiva no Astral},
  wwwlink={https://unilaiva-astral.aavalla.net/},
  wwwqr={QR_https_unilaiva-astral_aavalla_net.png},
  author={unilarva},
  subject={Songbook},
  keywords={songbook, songs, hinos, spiritual, entheogens, ceremony, Santo Daime},
  language={portuguese},
  bindingoffset={7mm}
}{ulsbs-songbook}

% NOTE: QR image created with:
%       qrencode -s 32 -l Q -o content/img/QR_https_unilaiva-astral_aavalla_net.png "https://unilaiva-astral.aavalla.net/"
%       --> then added the Unilaiva no Astral icon in the middle as 320x320 image with borders

% Handle size/side: force 10pt,twoside; accept them silently; ignore conflicts
\DeclareOption{10pt}{}
\DeclareOption{11pt}{\ClassWarning{ulsbs-songbook-astral-default}{Ignoring 11pt; forcing 10pt}}
\DeclareOption{12pt}{\ClassWarning{ulsbs-songbook-astral-default}{Ignoring 12pt; forcing 10pt}}
\DeclareOption{oneside}{\ClassWarning{ulsbs-songbook-astral-default}{Ignoring oneside; forcing twoside}}
\DeclareOption{twoside}{}

% Process child keys first, then forward the rest
\ProcessKeyvalOptions*
\ProcessOptions\relax


% LOAD THE PARENT CLASS
\LoadClass[10pt,twoside,openright,onecolumn]{ulsbs-songbook}


% ULSBS setup:

% Set things shown on the second page:
\renewcommand{\bookmotto}{\ifchorded{com informação musical}\fi}
\renewcommand{\bookbytext}{%
  Recebido por:\par\vspace{0.618034ex}\textbf{\Large humanidade}%
}%
\renewcommand{\bookcompiledbytext}{%
  Compilado por: unilarva (\href{mailto:lari.natri@iki.fi}{lari.natri@iki.fi})%
  \imagec[5]{larva_avatar.png}%
}%
\renewcommand{\imprintpagefootnote}{%
  Unilaiva no Astral é um projeto que tem como objetivo transcrever hinários
  comumente cantados em um formato que contenha todas as informações musicais,
  incluindo partituras, mas que seja fácil e conveniente de usar para praticar e no
  trabalho também. Isso é possível com a ajuda de muitas pessoas --- e através do canto,
  da execução, da dança, da escuta, da partilha, do estudo e da aprendizagem. Este é
  um trabalho em andamento que está sendo realizado com Amor e um sentimento imenso de
  Gratidão em relação ao belo Multidão de Hinos, às pessoas que os receberam, à Doutrina
  e ao incrível \mbox{Mistério do Universo}.
}

\renewcommand\chaptersymbol{%
  {\symboliifont 🟌}%
}

% Setup the mark at song end, just above the horizontal line that ends a song;
% if this macro is empty (the default), only the line is displayed.
\renewcommand{\songendmark}{%
  \symboliifont 🌣 \symbolfont ☾ \symboliifont 🟋%
}

% Make tag list in the prelude bold, and use the same style for chorded and
% lyric books
\renewcommand\preludetagstyle{\bfseries}

% Setup the icons displayed on the front cover
\renewcommand{\tagiconchords}{ulsbs-tag-icon-chords_PT_512x512px.png}
\renewcommand{\tagiconlyricsonly}{ulsbs-tag-icon-lyrics-only_PT_512x512px.png}
\renewcommand{\insertcovericons}{\insertcovericonsvtl}%

\renewcommand{\translationfont}{\footnotesize} % make translated text smaller
\renewcommand\mnalttagtext{2} % put "2" as tag for alternate melody notes
% larger chord font:
\renewcommand{\chordfont}{\sffamily\bfseries\normalsize\color{chordcolor}}
% smaller explanation font:
\renewcommand{\explanationfont}{\rmfamily\scriptsize}

% Do not display language *code* for PT
\renewcommand{\passageomitlangcodes}{PT}
\renewcommand{\explanationomitlangcodes}{PT}

% polyglossia: language settings
\setmainlanguage[variant=brazilian]{portuguese}
\setotherlanguage{english}
\setotherlanguage{finnish}

\showphfalse
\showphintocfalse
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

% Setup chapter colors
\definecolor{chapprecescolor}{rgb}{.196,.5176,.749} % from the image
\definecolor{chaporacaocolor}{rgb}{.749,.749,.749}
\definecolor{chapconcentracaocolor}{rgb}{.2078,.4156,.3725}
\definecolor{chapconcentracaodiversoscolor}{rgb}{.3803,.7607,.6784}
\definecolor{chapdaimecolor}{rgb}{0,.5,0}
\definecolor{chapsantamariacolor}{rgb}{0,0,.5}
\definecolor{chapcuraicolor}{rgb}{.1725,.5686,.0039}
\definecolor{chapcuraiicolor}{rgb}{.2627,.8627,.0078}
\definecolor{chapcuradiversoscolor}{rgb}{.6627,.8627,0}
\definecolor{chapsaomiguelcolor}{rgb}{.5490,0,1}
\definecolor{chapdiversoscolor}{rgb}{.7843,.7843,.5490}
\definecolor{chapcruzeirinhocolor}{rgb}{.9529,.7843,0}
\definecolor{chapencerramentocolor}{rgb}{0,.7647,1}
\definecolor{chapdefumacaocolor}{rgb}{.8475,.3019,.848}
\definecolor{chapaniversariocolor}{rgb}{1,.5,0}
\definecolor{chapmestrecolor}{rgb}{0,.086,.667}
\definecolor{chapmestrediversoescolor}{rgb}{1,.9921,.7058}
\definecolor{chapnovaeracolor}{rgb}{.7,.26,0}
\definecolor{chapnovadimensaocolor}{rgb}{.9,.5,0}
\definecolor{chapochaveiraocolor}{rgb}{.3529,.98,.4078}
\definecolor{chaprevelacaocolor}{rgb}{1,1,1} % = white = invisible
\definecolor{chaprosariocolor}{rgb}{.15,.7,.15}
\definecolor{chapluabrancacolor}{rgb}{.8133,.1752,.7921}
\definecolor{chapultioscolor}{rgb}{0,.4039,.933}
\definecolor{chapuldiversoscolor}{rgb}{.4313,0,.49}
\definecolor{chapultransparenciacolor}{rgb}{.98,.7722,.2067}
% Override language colors
\definecolor{astralenglishcolor}{rgb}{0,0.26,0.26}%
\colorlet{langportuguesecolor}{black}%
\colorlet{langenglishcolor}{astralenglishcolor}%


% Adds a note about the rest in this chapter not being in other books. Use
% this within a song chapter, but outside of songs.
\newcommand{\noteulspecific}{%
  \begin{intersong}
    \vfill
    \begin{explanation}[PT]\sffamily\normalsize
      A partir deste ponto em diante, o capítulo atual possui adições específicas
      de \textbf{Unilaiva}, que podem não estar presentes em outros livros.
    \end{explanation}
    \begin{explanation}[EN]\sffamily\normalsize
      From this point onward, the current chapter has \textbf{Unilaiva} specific
      additions, which might not be present in other books.
    \end{explanation}
    \vfill
  \end{intersong}
}
