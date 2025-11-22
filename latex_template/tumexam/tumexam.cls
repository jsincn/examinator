%% tumexam.cls
%
% This work may be distributed and/or modified under the conditions of
% the LaTeX Project Public License, either version 1.3 of this license
% or (at your option) any later version.
% The latest version of this license is in
%   http://www.latex-project.org/lppl.txt
% and version 1.3 or later is part of all distributions of LaTeX version
% 2005/12/01 or later.
%
% This work has the LPPL maintenance status `maintained'.
%
% The Current Maintainer of this work is Stephan Günther.
%
% Copyright 2016-2022 Chair of Network Architectures and Services, TUM
%
% This work consists of the files listed in manifest.txt.

\NeedsTeXFormat{LaTeX2e}
\ProvidesClass{tumexam}[2021/09/28 TUMexam]

\LoadClassWithOptions{article}

\RequirePackage{geometry}
\RequirePackage[hidelinks]{hyperref}
\RequirePackage{afterpage}
\RequirePackage{pifont}
\RequirePackage{xstring}
\RequirePackage{tikz}
\usetikzlibrary{patterns}
\usetikzlibrary{calc}
\RequirePackage[pagestyles,extramarks]{titlesec}
\RequirePackage{datamatrix}
\RequirePackage{storebox}
\AtBeginDocument{{}} % due to https://tex.stackexchange.com/a/141540
\RequirePackage{rotating}
\RequirePackage{ifoddpage}
\RequirePackage{marginfit}
\RequirePackage{pdfpages}
\RequirePackage{csvsimple}
\RequirePackage{atbegshi}
\@ifundefined{AddToHook}{%
	\RequirePackage{everypage}
}

\RequirePackage{tumexam/examconf}
\RequirePackage{tumexam/scanconf}
\RequirePackage{tumexam/creditbox}
\RequirePackage{tumexam/jobname}
\RequirePackage{tumexam/savepos}
\RequirePackage{tumexam/misc}
\RequirePackage{tumexam/sticker}

\RequirePackage{tumfonts}
\RequirePackage{tumcontact}

\AtBeginDocument{%
	\@ifpackageloaded{fullpage}%
	{\ClassError{tumexam}{You loaded the package fullpage, which overrides pagestyles. Do not use fullpage with tumexam}%
		{Do not use fullpage with tumexam}\@@end}%
	{}%
	\IfFileExists{conf/examconf.tex}{%
	{\ClassError{tumexam}{Found file conf/examconf.tex, which will be ignored since WiSe 2021. Please read the documentation / changelog}%
		{}\@@end}%
	}{}
	\IfFileExists{conf/code.tex}{%
	{\ClassError{tumexam}{Found file conf/examconf.tex, which will be ignored since WiSe 2021. Please read the documentation / changelog}%
		{}\@@end}%
	}{}
}


\checkjobname{solution}
\checkjobname{example}
\checkjobname{correction}
\checkjobname{examids}
\ifcorrection
	\solutiontrue
\fi
\ifexamids
	\examidstrue
\fi


\ifsingleside
\@ifundefined{AddToHook}{%
	\AddEverypageHook{%
		\checkoddpage%
		\ifoddpage%
			\AtBeginShipoutNext{\newpage\null\newpage}%
		\fi%
	}%
}{%
	\AddToHook{shipout/before}{%
		\ifodd\c@page%
			\newpage\null\newpage%
		\fi%
	}%
}
\fi


% We want
% - neither dmcodes nor pagecodes in the footer for targets exam, solution, and
%   correction,
% - no dmcodes but pagecodes for solutionids,
% - both dmcodes and pagecodes for examids, example, protocols, and
%   attendeelists, and
% - \tumexam@eid should expand to the jobname for all targets but examids and
%   solutionids.
% \tumexam@eid is set to the respective jobname and cleared if there is no
% integer supplied *and* target is not example. This makes \tumexam@pid expand
% to nothing.

\edef\tumexam@eid{\tumexam@jobname}
\edef\tumexam@erid{E\tumexam@jobname}
\newif\iftumexam@pagecode

\IfInteger{\tumexam@jobname@extra}{
	\ifsolution\else%
		\tumexam@pagecodetrue
	\fi
	\edef\tumexam@erid{E\tumexam@jobname@extra}
	\edef\tumexam@eid{\tumexam@jobname@extra}
}{
	\tumexam@pagecodefalse
	\ifexample\relax\else
		\edef\tumexam@eid{}
	\fi
}
\ifexample
	\tumexam@pagecodetrue
\fi


\setlength\parindent{0pt}


\newcommand{\tumexam@dimensions@setup}{%
	\setlength{\global\@colht}{\textheight}%
	\setlength{\global\@colroom}{\textheight}%
	\setlength{\global\vsize}{\textheight}%
	\setlength{\global\columnwidth}{\textwidth}%
	\if@twocolumn%
		\addtolength{\columnwidth}{-\columnsep}%
		\global\divide\columnwidth\tw@%
		\global\@firstcolumntrue
	\fi%
	\setlength{\global\hsize}{\columnwidth}%
	\setlength{\global\linewidth}{\hsize}%
}


% We sometimes insert pages at the front (or at the end) that should not be
% counted but of course we still need unique page numbers for example for the
% page codes or the generated CSVs. To avoid messing with the page counter
% defined by Latex, we define our own here that is only used for display
% purposes.
% Note that this will seemingly break \pageref as that uses the original page
% counter and not the tumexam@displaypage counter that is used to display the
% page number at the bottom of each page. However, messing with the page
% counter would break things like hyperref, \cleardoublepage and of course our
% own page codes and the generated CSVs.
\newcounter{tumexam@displaypage}
\@ifundefined{AddToHook}{%
	\AddEverypageHook{\addtocounter{tumexam@displaypage}{1}}
	\def\tumexam@reset@displaypage{%
		\setcounter{tumexam@displaypage}{0}%
	}
}{%
	\AddToHook{shipout/before}{\addtocounter{tumexam@displaypage}{1}}
	\def\tumexam@reset@displaypage{%
		% In the new latex version the hooks are only ran after each page, so
		% we need to initialize the counter to 1.
		\setcounter{tumexam@displaypage}{1}%
	}
}
\tumexam@reset@displaypage

% Newer LaTeX versions define the totalpage counter themselves, so don't
% redefine it. It has slightly different semantics than what we would expect
% (it always is incremented at each page), so we define our own counter that
% deals with that. Also, we don't want to count the pages in the backcover,
% which is implemented in the \backcover command.
\newcounter{tumexam@totalpages}
\AtEndDocument{\immediate\write\@auxout{\global\c@tumexam@totalpages \thetumexam@displaypage\relax}}

\newcommand{\tumexam@pid}{%
	\ifx\tumexam@eid\empty%
		\relax%
	\else%
		\examcode-\tumexam@erid-\twodigit{\c@page}%
	\fi%
}

\iftumexam@pagecode
	\newcounter{tumexam@dm@page}

	\def\tumexam@generatedm{%
		\setcounter{tumexam@dm@page}{\thepage}%
		\storebox{\tumexam@dm@storebox@tmp}{\datamatrix*[.4167mm]{\tumexam@pid}}%
		\global\let\tumexam@dm@storebox\tumexam@dm@storebox@tmp%
	}

	\newcommand{\tumexam@dm}{%
		% Lazily generate the new datamatrix
		\ifnum\thetumexam@dm@page=\thepage\else%
			\tumexam@generatedm%
		\fi
		\usestorebox{\tumexam@dm@storebox}%
	}
\else
        \newcommand{\tumexam@dm}{}
\fi

\iftumexam@pagecode
	\iftumexam@staple
		\@ifundefined{AddToHook}{%
			\AddEverypageHook{\tumexam@makecutmarks}
		}{%
			\AddToHook{shipout/background}{\tumexam@makecutmarks}
		}
	\fi
\fi


\newpagestyle{tumexam@cover}{%
	\sethead[%
		\iftumexam@pagecode%
			\hspace*{-20mm}\scanconf@pagecode{UL}\datamatrix[.4545mm]{\tumexam@pid}%
		\fi%
	][%
		\TUMheader[black]{10mm}%
	][%
	]{%
	}{%
		\TUMheader[black]{10mm}%
	}{%
		\iftumexam@pagecode%
			\scanconf@pagecode{UR}\datamatrix[.4545mm]{\tumexam@pid}\hspace*{-20mm}%
		\fi
	}%
	\setfoot[%
		\iftumexam@pagecode%
			\mbox{\hspace*{-20mm}\scanconf@pagecode{BL}\tumexam@dm\hspace{5mm}\texttt{\scriptsize\tumexam@pid}}%
		\fi%
	][%
	][%
		\iftumexam@pagecode%
			\mbox{\scanconf@pagecode{BR}\tumexam@dm}%
		\fi%
	]{%
		\iftumexam@pagecode%
			\mbox{\scanconf@pagecode{BL}\tumexam@dm}%
		\fi%
	}{%
	}{%
		\iftumexam@pagecode%
			\mbox{\texttt{\scriptsize\tumexam@pid}\hspace{5mm}\scanconf@pagecode{BR}\tumexam@dm\hspace*{-20mm}}%
		\fi%
		\ifsolution%
			\mbox{\texttt{\scriptsize\tumexam@pid}}%
		\fi%
	}%
}
\newpagestyle{tumexam@title}{%
	\sethead[%
		\iftumexam@pagecode%
			\hspace*{-20mm}\scanconf@pagecode{UL}\datamatrix[.4545mm]{\tumexam@pid}%
		\fi%
	][%
		\TUMheader[black]{10mm}%
	][%
	]{%
	}{%
		\TUMheader[black]{10mm}%
	}{%
		\iftumexam@pagecode%
			\scanconf@pagecode{UR}{}\datamatrix[.4545mm]{\tumexam@pid}\hspace*{-20mm}%
		\fi
	}%
	\setfoot[%
		\iftumexam@pagecode%
			\mbox{\hspace*{-20mm}\scanconf@pagecode{BL}\tumexam@dm\hspace{5mm}\texttt{\scriptsize\tumexam@pid}}%
		\fi%
	][%
		\normalfont{-- \pagename{} \thetumexam@displaypage\ / \normalfont\thetumexam@totalpages\ --}%
	][%
		\iftumexam@pagecode%
			\mbox{{\scriptsize\examemptytext}~\tikz{\tumexam@crossbox{0}{0}{e\thepage}{-1}}\hspace{5mm}\scanconf@pagecode{BR}\tumexam@dm}%
		\fi%
	]{%
		\iftumexam@pagecode%
			\mbox{\scanconf@pagecode{BL}\tumexam@dm\hspace{5mm}\tikz{\tumexam@crossbox{0}{0}{e\thepage}{-1}}~{\scriptsize\examemptytext}}%
		\fi%
	}{%
		\normalfont{-- \pagename{} \thetumexam@displaypage\ / \normalfont\thetumexam@totalpages\ --}%
	}{%
		\iftumexam@pagecode%
			\mbox{\texttt{\scriptsize\tumexam@pid}\hspace{5mm}\scanconf@pagecode{BR}\tumexam@dm\hspace*{-20mm}}%
		\fi%
		\ifsolution%
			\mbox{\texttt{\scriptsize\tumexam@pid}}%
		\fi%
	}%
}
\newpagestyle{tumexam}{%
	\sethead[%
		\iftumexam@pagecode%
			\iftumexam@landscape\else%
				\hspace{-15mm}\hspace{-\marginparsep}%
			\fi%
			\scanconf@pagecode{UL}\tumexam@dm%
		\fi%
	][%
	][%
	]{%
	}{%
	}{%
		\iftumexam@pagecode%
			\scanconf@pagecode{UR}\tumexam@dm%
			\iftumexam@landscape\else%
				\hspace{-15mm}\hspace{-\marginparsep}%
			\fi%
		\fi
	}%
	\setfoot[%
		\iftumexam@pagecode%
			\mbox{%
				\iftumexam@landscape\else%
					\hspace{-15mm}\hspace{-\marginparsep}%
				\fi%
				\scanconf@pagecode{BL}\tumexam@dm%
				\ifexternalproblems%
					\hspace{5mm}%
				\else%
					\hspace{\marginparsep}%
				\fi%
				\texttt{\scriptsize\tumexam@pid}%
			}%
		\fi%
		\ifsolution%
			\mbox{\texttt{\scriptsize\tumexam@pid}}%
		\fi%
	][%
		\normalfont{-- \pagename{} \thetumexam@displaypage\ / \normalfont\thetumexam@totalpages\ --}%
	][%
		\iftumexam@pagecode%
			\mbox{%
				{\scriptsize\pageemptytext}~\tikz{\tumexam@crossbox{0}{0}{e\thepage}{-1}}%
				\ifexternalproblems%
					\hspace{5mm}%
				\else%
					\hspace{\marginparsep}%
				\fi%
				\scanconf@pagecode{BR}\tumexam@dm%
			}%
		\fi%
	]{%
		\iftumexam@pagecode%
			\mbox{%
				\scanconf@pagecode{BL}\tumexam@dm%
				\ifexternalproblems%
					\hspace{5mm}%
				\else%
					\hspace{\marginparsep}%
				\fi%
				\tikz{\tumexam@crossbox{0}{0}{e\thepage}{-1}}~{\scriptsize\pageemptytext}%
			}%
		\fi%
	}{%
		\normalfont{-- \pagename{} \thetumexam@displaypage\ / \normalfont\thetumexam@totalpages\ --}%
	}{%
		\iftumexam@pagecode%
			\mbox{%
				\texttt{\scriptsize\tumexam@pid}%
				\ifexternalproblems%
					\hspace{5mm}%
				\else%
					\hspace{\marginparsep}%
				\fi%
				\scanconf@pagecode{BR}\tumexam@dm%
				\iftumexam@landscape\else%
					\hspace{-15mm}\hspace{-\marginparsep}%
				\fi%
			}%
		\fi%
		\ifsolution%
			\mbox{\texttt{\scriptsize\tumexam@pid}}%
		\fi%
	}%
}
\newpagestyle{tumexam@empty}{%
	\sethead[%
		\iftumexam@pagecode%
			\iftumexam@landscape\else%
				\hspace{-15mm}\hspace{-\marginparsep}%
			\fi%
			\scanconf@pagecode{UL}\tumexam@dm%
		\fi%
	][%
	][%
	]{%
	}{%
	}{%
		\iftumexam@pagecode%
			\scanconf@pagecode{UR}\tumexam@dm%
			\iftumexam@landscape\else%
				\hspace{-15mm}\hspace{-\marginparsep}%
			\fi%
		\fi
	}%
	\setfoot[%
		\iftumexam@pagecode%
			\mbox{%
				\iftumexam@landscape\else%
					\hspace{-15mm}\hspace{-\marginparsep}%
				\fi%
				\scanconf@pagecode{BL}\tumexam@dm%
				\ifexternalproblems%
					\hspace{5mm}%
				\else%
					\hspace{\marginparsep}%
				\fi%
				\texttt{\scriptsize\tumexam@pid}%
			}%
		\fi%
	][%
	][%
		\iftumexam@pagecode%
			\mbox{\scanconf@pagecode{BR}\tumexam@dm}%
		\fi%
	]{%
		\iftumexam@pagecode%
			\mbox{\scanconf@pagecode{BL}\tumexam@dm}%
		\fi%
	}{%
	}{%
		\iftumexam@pagecode%
			\mbox{%
				\texttt{\scriptsize\tumexam@pid}%
				\ifexternalproblems%
					\hspace{5mm}%
				\else%
					\hspace{\marginparsep}%
				\fi%
				\scanconf@pagecode{BR}\tumexam@dm%
				\iftumexam@landscape\else%
					\hspace{-15mm}\hspace{-\marginparsep}%
				\fi%
			}%
		\fi%
	}%
}

\pagestyle{tumexam}

\newcommand{\tumexam@geometry@portrait}{%
	\newgeometry{
		top=16.667mm,
		bottom=16.667mm,
		outer=\ifexternalproblems20mm\else25mm\fi,
		inner=\iftumexam@staple20mm\else10mm\fi,
		columnsep=5mm,
		marginparwidth=\creditboxwidth,
		marginparsep=\ifexternalproblems0mm\else5mm\fi,
		headheight=6.667mm,
		headsep=5mm,
		footskip=11.667mm,
		twoside=true,
	}%
	\tumexam@dimensions@setup%
}
\newcommand{\tumexam@geometry@landscape}{%
	\setlength{\@tempskipb}{\creditboxwidth}%
	\ifexternalproblems\else%
		\addtolength{\@tempskipb}{5mm}%
	\fi%
	\setlength{\@tempskipa}{16.667mm}%
	\addtolength{\@tempskipa}{\@tempskipb}%
	\edef\tumexam@geometry@margin{\the\@tempskipa}%
	\setlength{\@tempskipa}{5mm}%
	\addtolength{\@tempskipa}{\@tempskipb}%
	\edef\tumexam@geometry@headsep{\the\@tempskipa}%
	\setlength{\@tempskipa}{11.667mm}%
	\addtolength{\@tempskipa}{\@tempskipb}%
	\edef\tumexam@geometry@footskip{\the\@tempskipa}%
	\newgeometry{
		top=\tumexam@geometry@margin,
		bottom=\tumexam@geometry@margin,
		outer=5mm,
		inner=\iftumexam@staple20mm\else10mm\fi,
		columnsep=5mm,
		marginparwidth=\creditboxwidth,
		marginparsep=\ifexternalproblems0mm\else5mm\fi,
		headheight=6.667mm,
		headsep=\tumexam@geometry@headsep,
		footskip=\tumexam@geometry@footskip,
		twoside=true,
	}%
	\setlength{\hsize}{\textheight}%
	\setlength{\textheight}{\textwidth}%
	\setlength{\textwidth}{\hsize}%
	\tumexam@dimensions@setup%
}
\newcommand{\tumexam@geometry@title}{%
	\newgeometry{
		top=30mm,
		bottom=16.667mm,
		outer=25mm,
		inner=\iftumexam@staple20mm\else10mm\fi,
		columnsep=5mm,
		marginparwidth=\creditboxwidth,
		marginparsep=5mm,
		headheight=10mm,
		headsep=10mm,
		footskip=11.667mm,
		twoside=true,
	}%
	\tumexam@dimensions@setup%
	\afterpage{%
		\tumexam@geometry@portrait%
		\global\topmargin\topmargin%
		\global\headheight\headheight%
		\global\headsep\headsep%
		\global\textheight\textheight%
		\global\textwidth\textwidth%
		\global\oddsidemargin\oddsidemargin%
		\global\evensidemargin\evensidemargin%
		\global\marginparsep\marginparsep%
		\global\marginparwidth\marginparwidth%
	}%
}

\tumexam@geometry@portrait
\ifexternalproblems
	\setlength{\marginparpush}{1mm}
\else
	\setlength{\marginparpush}{2em}
\fi

\newif\iftumexam@landscape
\newenvironment{landscape}{%
	\tumexam@geometry@landscape%
	\tumexam@landscapetrue%
	\let\tumexam@outputpage\@outputpage%
	\def\@outputpage{%
		\setbox\@outputbox\hbox{\vbox{\rotatebox{90}{\box\@outputbox}}}%
		\begingroup%
		\setlength{\textwidth}{\textheight}%
		\renewcommand{\tumexam@setpos}[2]{%
			\tumexam@orig@setpos{####1}{####2}%
			\@tempskipa\lastxpos%
			\lastxpos\lastypos%
			\lastypos\pdfpagewidth%
			\advance\lastypos-\@tempskipa%
		}%
		\tumexam@outputpage%
		\endgroup%
	}%
	\pdfpageattr\expandafter{\the\pdfpageattr/Rotate 90}%
	\let\tumexam@orig@setpos\tumexam@setpos%
	\renewcommand{\tumexam@setpos}[2]{%
		\tumexam@orig@setpos{##1}{##2}%
		\advance\lastxpos-\textheight%
		\advance\lastxpos\Gm@bmargin%
		\advance\lastypos-\Gm@bmargin%
		\checkoddpage%
		\ifoddpage%
			\advance\lastxpos-\Gm@lmargin%
			\advance\lastypos\Gm@rmargin%
		\else%
			\advance\lastxpos-\Gm@rmargin%
			\advance\lastypos\Gm@lmargin%
		\fi%
	}%
}{%
	\tumexam@geometry@portrait%
}

\newcommand{\registrationsticker}{%
	\begin{tikzpicture}
		\node[rectangle,
			draw=black!40,
			pattern=north east lines,
			pattern color=black!20,
			minimum width=\sstickerwidth,
			minimum height=\sstickerheight,
		] (sticker) at (0,0) {};
		\node[color=black!60,above,font=\bfseries] at (0,0) {\tumexam@erid};
		\node[color=black!60,below,font=\scriptsize] at (0,0) {\ifsubmission\submissionnote\else\stickernote\fi};
	\end{tikzpicture}%
}

\newcommand{\submissionnotes}{%
	\personalizationnotessubmission\\
	\TextField[name=signaturefield,width=7cm,height=5mm,charsize=8pt,multiline=false,bordercolor=,backgroundcolor=,color=0 0.3725 0.7765]{\relax}\\[-\baselineskip]
	\vfill%
	\rule{10cm}{.5pt}\\[-.25\baselineskip]
	{\scriptsize \codeofconductsignature}
}

\renewcommand{\maketitle}{%
	\tumexam@geometry@title%
	\thispagestyle{tumexam@title}%
	\ifregistrationsticker%
		\begin{minipage}{\sstickerwidth}%
			\IfInteger{\tumexam@eid}{%
				\ifsubmission%
					\frame{\sticker{\examcode}{S\tumexam@eid}{}{}{}}%
				\else
					\registrationsticker%
				\fi
			}{%
				\registrationsticker%
			}
		\end{minipage}%
	\else%
			\registrationnumberbox%
	\fi%
	\hfill%
	\vtop{%
		\ifregistrationsticker%
			\addtolength{\hsize}{-\sstickerwidth}%
		\else%
			\addtolength{\hsize}{-14\tumexam@cboxwidth}%
		\fi%
		\addtolength{\hsize}{-3em}%
		\setlength{\linewidth}{\hsize}%
		\ifregistrationsticker\else%
			\vspace{0pt}%
			\frame{\phantom{\rule{15em}{3em}}}\\%
			{\tiny\signaturename}\\%
			\vspace{1em}\\%
		\fi%
		\footnotesize%
		\addtolength{\linewidth}{2em}
		\makeatletter
		\addtolength{\@totalleftmargin}{-2em}
		\makeatother
		\ifregistrationsticker%
			\begin{minipage}[c][\sstickerheight]{\textwidth-\sstickerwidth-4em}%
				\IfInteger{\tumexam@eid}{%
					\ifsubmission%
						\submissionnotes%
					\else%
						\textbf{\personalizationnotesname:}
						\personalizationnotessticker%
					\fi
				}{%
					\ifsubmission%
						\submissionnotes%
					\else%
						\textbf{\personalizationnotesname:}
						\personalizationnotessticker%
					\fi
				}
			\end{minipage}
		\else%
			\textbf{\personalizationnotesname:}
			\personalizationnotesbox%
		\fi%
	}%

	\ifnotitle\else%
		\vspace{4em}%
		\begin{center}
			\textbf{\LARGE \thetitle}
		\end{center}
		\renewcommand{\arraystretch}{1.2}
		\null\hfill
		\begin{tabular}{llp{0.5em}ll}
			\textbf{\examname:} & \themodule\ / \thetype &&
			\textbf{\datename:} & \theexamdate \\
			\textbf{\examinername:} & \theexaminer &&
			\textbf{\timename:} & \thestarttime~--~\thestoptime
		\end{tabular}
		\hfill\null%
	\fi%
	\vskip4em

}

\newcommand{\tumexam@cover}{%
	\maketitle%
	\vspace{-\lastskip}
	\vspace{\fill}

	\ifnocorrectorbox\else
		\hbox to \hsize {\hss%
		\begin{tikzpicture}
			\ifnum\thetotalproblems>8
				\ifnum\thetotalproblems>10
					\def\tumexam@covercorr@width{1cm}
				\else
					\def\tumexam@covercorr@width{1.5cm}
				\fi
			\else
				\def\tumexam@covercorr@width{2cm}
			\fi
			\node[left] at (0.5*\tumexam@covercorr@width-0.2cm,-1cm) {\correctionpassa};
			\ifsinglepass\else
				\node[left] at (0.5*\tumexam@covercorr@width-0.2cm,-2cm) {\correctionpassb};
			\fi
			\foreach \x in {1,...,\thetotalproblems} {
				\node at (\x*\tumexam@covercorr@width,0) {\localetext{P}{A}~\x};
				\node[
					draw,
					rectangle,
					minimum width=\tumexam@covercorr@width+0.5pt,
					minimum height=1cm,
					line width=1pt
				] at (\x*\tumexam@covercorr@width,-1cm) {};
				\ifsinglepass\else
					\node[
						draw,
						rectangle,
						minimum width=\tumexam@covercorr@width-0.5pt,
						minimum height=1cm-1pt,
						line width=2pt
					] at (\x*\tumexam@covercorr@width,-2cm) {};
				\fi
			}
		\end{tikzpicture}%
		\hss}%
		\vspace{\fill}
	\fi

}
\newcommand{\tumexam@covernotes}{%
	\ifsubmission\relax\else%
		\frame{%
			\advance\hsize-3pt
			\ifcoversheet%
				\hbox to \hsize {\hss%
					\begin{tabular}{ll}
							& \\[0.5em]
						\localetext{Left room}{H\"orsaal verlassen}
							&
						\localetext{from}{von} \ \rule[-1mm]{3cm}{1pt} \ %
						\localetext{to}{bis} \ \rule[-1mm]{3cm}{1pt}\\[2em]
							&
						\localetext{from}{von} \ \rule[-1mm]{3cm}{1pt} \ %
						\localetext{to}{bis} \ \rule[-1mm]{3cm}{1pt}\\[3em]
						\localetext{Early submission}{Vorzeitige Abgabe}
							&
						\localetext{at}{um} \ \rule[-1mm]{3cm}{1pt}\\[3em]
						\localetext{Notes}{Anmerkungen}
							&
						\rule[-1mm]{12cm}{1pt}\\[0.5em]
					\end{tabular}%
				\hss}

			\else%
				\vbox{
					\vspace{1em}
					\hspace*{1em}%
					\localetext{Left room}{H\"orsaal verlassen}
					\localetext{from}{von} \ \rule[-1mm]{2cm}{1pt} \ %
					\localetext{to}{bis} \ \rule[-1mm]{2cm}{1pt}
					\hfil / \hfil
					\localetext{Early submission}{Vorzeitige Abgabe}
					\localetext{at}{um} \ \rule[-1mm]{2cm}{1pt}
					\vspace{0.5em}
				}
			\fi%
		}
	\fi
}

\renewenvironment{titlepage}{%
	\tumexam@cover%
	\ifcoversheet%
		\pagestyle{tumexam@empty}%
		\thispagestyle{tumexam@cover}%
		\tumexam@covernotes%

		\clearpage%

		\cleardoublepage%
		\tumexam@reset@displaypage%
		\tumexam@geometry@title%
		\pagestyle{tumexam}%
		\thispagestyle{tumexam@title}%

		\vspace*{2em}
		\huge\begin{center}
		    \fontsize{20}{22}\textbf{\thetype}

		    \vspace{1em}
		    \selectfont\textbf{\thetitle}
		\end{center}

		\vspace{1em}
		\large\begin{center}
		    \theexaminer\\
		    \thechair\\
		    \thedepartment\\
		    \orgname
		\end{center}

		\vspace{1em}
		\Large\begin{center}
			\textbf{\theexamdate} \\
		\textbf{\thestarttime~--~\thestoptime}
		\end{center}

		\normalsize
		\vspace{\fill}

	\fi%
}{
	\vspace*{\fill}
	\ifcoversheet\else%
		\tumexam@covernotes%
	\fi%
	\clearpage%
}


\renewcommand{\theproblem}{\arabic{problem}}
\ifsubproblemarabic
	\renewcommand{\thesubproblem}{%
		\ifnum\c@totalproblems=1\relax%
			\arabic{subproblem}.%
		\else%
			\theproblem.\arabic{subproblem}%
		\fi%
	}
\else
	\renewcommand{\thesubproblem}{\alph{subproblem})}
\fi
\newcommand{\tumexam@problemid}{\theproblem.\arabic{subproblem}.\arabic{subproblemsolutionbox}}

\@addtoreset{figure}{problem}
\@addtoreset{table}{problem}
\@addtoreset{equation}{problem}
\renewcommand{\thefigure}{\arabic{problem}.\arabic{figure}}
\renewcommand{\thetable}{\arabic{problem}.\arabic{table}}
\renewcommand{\theequation}{\arabic{problem}.\arabic{equation}}

\newcounter{totalproblems}
\AtEndDocument{\immediate\write\@auxout{\global\c@totalproblems \arabic{problem}\relax}}

\newlength{\totalcredits}
\newcommand{\thetotalcredits}{\credits{\totalcredits}}
\newlength{\tumexam@totalcredits}
\AtEndDocument{\immediate\write\@auxout{\global\totalcredits \the\tumexam@totalcredits\relax}}

\newcommand{\tumexam@problemsubproblemcounter}[1]{
	\expandafter\newcount\csname tumexam@problemsubproblems#1\endcsname%
	\ifcsname thetumexam@problemsubproblems#1\endcsname\else%
		\expandafter\edef\csname thetumexam@problemsubproblems#1\endcsname{0}%
	\fi%
	\AtEndDocument{%
		\immediate\write\@auxout{\global\string\expandafter\string\edef\string\cs name thetumexam@problemsubproblems#1\string\endcs name {\expandafter\the\csname tumexam@problemsubproblems#1\endcsname}}%
	}%
}

\newcommand{\tumexam@problemcreditscounter}[1]{
	\ifcsname tumexam@problemcredits#1\endcsname\else%
		\expandafter\newskip\csname tumexam@problemcredits#1\endcsname%
	\fi%
	\AtEndDocument{%
		\immediate\write\@auxout{\string\expandafter\string\newskip\string\cs name tumexam@problemcredits#1\string\endcsname}%
		\immediate\write\@auxout{\expandafter\global\string\cs name tumexam@problemcredits#1\string\endcs name \expandafter\the\csname tumexam@problemcredits#1\endcsname\relax}%
	}%
}

\newcommand{\credits}[1]{\strip@pt#1~\ifdim#1=1pt\creditname\else\creditsname\fi}

\newcommand{\problem}[1]{
	\refstepcounter{problem}%
	\edef\tumexam@theproblem{\arabic{problem}}
	\expandafter\tumexam@problemsubproblemcounter\expandafter{\tumexam@theproblem}
	\expandafter\tumexam@problemcreditscounter\expandafter{\tumexam@theproblem}
	\ifnoproblem\else%
		{%
			\bfseries%
			{%
				\ifexternalproblems%
					\normalsize%
				\else%
					\Large%
				\fi%
				\problemname~\theproblem%
			}%
			\quad#1 %
			\ifnoproblemcredits\else%
				(\credits{\csname tumexam@problemcredits\arabic{problem}\endcsname})%
			\fi%
		}%
		\ifexternalproblems\else%
			\vskip.5\baselineskip%
		\fi%
	\fi%
	\label{\problemname\theproblem}
	\addtocontents{toc}{\hyperref[\problemname\theproblem]{\theproblem.\ #1 (\credits{\csname tumexam@problemcredits\arabic{problem}\endcsname})\dotfill\thetumexam@displaypage}\\[1ex]}
	\csname tumexam@problemcredits\arabic{problem}\endcsname 0pt\relax%
}

\newcommand{\tumexam@subproblem@credits}[2]{%
	\expandafter\global\csname tumexam@problemsubproblems\arabic{problem}\endcsname \c@subproblem\relax%
	\global\advance\tumexam@totalcredits#1pt\relax%
	\expandafter\global\expandafter\advance\csname tumexam@problemcredits\arabic{problem}\endcsname #1pt\relax%
	\ifsubproblemarabic%
		\scanconf@subproblem{\arabic{problem}}{\arabic{subproblem}}{#1}{#2}%
	\else%
		\scanconf@subproblem{\arabic{problem}}{\alph{subproblem}}{#1}{#2}%
	\fi%
}

\newcommand{\tumexam@subproblem@creditbox@margin}[2]{%
	\ifexternalproblems\else%
		\vspace{-0.7em}%
	\fi%
	\begin{tikzpicture}[baseline={(0,0)}]
		\creditbox#2{#1}
	\end{tikzpicture}%
}

\def\subproblem{\@ifstar{\subproblem@i{*}}{\subproblem@i{}}}
\newcommand{\subproblem@i}[1]{%
	\vskip1em%
	\refstepcounter{subproblem}%
	\ifnum\csname thetumexam@problemsubproblems\arabic{problem}\endcsname=1%
		\strut%
	\else%
		\thesubproblem#1\ %
	\fi%
	\subproblem@ii%
}
\def\tumexam@subproblem@calccredit{credit}
\newcommand{\subproblem@ii}[2][\tumexam@subproblem@calccredit]{%
	\edef\tumexam@subproblem@calc{#1}%
	\tumexam@subproblem@credits{#2}{#1}%
	\ifx\tumexam@subproblem@calc\tumexam@subproblem@calccredit%
		\marginpar[\tumexam@subproblem@creditbox@margin{#2}{*}]{\tumexam@subproblem@creditbox@margin{#2}{}}%
	\fi%
	\ignorespaces%
}

\newlength{\solutionboxmargin}
\newlength{\solutionboxheight}
\newlength{\solutionboxinputwidth}
\ifexternalproblems
	\setlength{\solutionboxmargin}{1mm}
\else
	\setlength{\solutionboxmargin}{5mm}
\fi
\newbox\tumexam@solutionbox
\newbox\tumexam@gridbox
\newcommand{\tumexam@beginsolutionbox}[1]{%
	\setlength{\solutionboxheight}{#1}%
	\setlength{\solutionboxinputwidth}{\hsize}%
	\addtolength{\solutionboxinputwidth}{-2mm}% FIXME unclear where this comes from
	\setbox\tumexam@solutionbox\vbox to #1 \bgroup%
		\vskip\solutionboxmargin%
		\hskip\solutionboxmargin%
		\vbox\bgroup%
			\addtolength{\hsize}{-2\solutionboxmargin}%
			\setlength{\columnwidth}{\hsize}%
			\setlength{\linewidth}{\hsize}%
}
\newcommand{\tumexam@endsolutionbox}{%
		\egroup%
		\hskip\solutionboxmargin%
		\vfill%
	\egroup%
}
\ifexternalproblems
	\newcommand{\tumexam@startsolutionbox}[2]{%
		\stepcounter{subproblemsolutionbox}%
		\vskip0pt%
		\ifdim#2pt=0pt\else%
			\refstepcounter{subproblem}%
			\subproblem@ii{#2}%
		\fi%
		\tumexam@beginsolutionbox{#1}%
		\ifdim#2pt=0pt\else%
			\ifnum\csname thetumexam@problemsubproblems\arabic{problem}\endcsname=1%
				\strut%
			\else%
				\thesubproblem\ %
			\fi%
		\fi%
	}
\else
	\newcommand{\tumexam@startsolutionbox}[1]{%
		\stepcounter{subproblemsolutionbox}%
		\vskip1ex%
		\tumexam@beginsolutionbox{#1}%
	}
\fi
\newenvironment{solutionbox}[1][20mm]{%
	\tumexam@startsolutionbox{#1}%
}{%
	\tumexam@endsolutionbox%
	\frame{%
		\box\tumexam@gridbox%
		\begingroup%
			\ifsolution%
				\color{blue}%
				\box\tumexam@solutionbox%
			\else%
				\iftumexam@landscape
					\def\tumexam@rotation{90}
				\else
					\def\tumexam@rotation{0}
				\fi
				\TextField[rotation=\tumexam@rotation,name=\tumexam@problemid,width=\solutionboxinputwidth,height=\solutionboxheight,charsize=8pt,multiline=true,bordercolor=,backgroundcolor=,color=0 0.3725 0.7765]{\relax}%
			\fi%
		\endgroup%
	}%
}
\newenvironment{instructionbox}[1][20mm]{%
	\solutionbox[#1]%
}{%
	\tumexam@endsolutionbox%
	\frame{%
		\box\tumexam@gridbox%
		\box\tumexam@solutionbox%
	}%
}
\newcommand{\tumexam@setgridbox}[1]{%
	\setbox\tumexam@gridbox\hbox to 0pt {%
		\begin{tikzpicture}
			\useasboundingbox (0,0) rectangle (\hsize,#1);
			\draw[step=\gridsize,black!50] (0,0) grid (\hsize,#1);
		\end{tikzpicture}%
		\hskip 0pt minus 1fill%
	}%
}
\newenvironment{gridsolutionbox}[1][20mm]{%
	\tumexam@setgridbox{#1}%
	\solutionbox[#1]%
}{%
	\endsolutionbox%
}
\newenvironment{gridinstructionbox}[1][20mm]{%
	\tumexam@setgridbox{#1}%
	\instructionbox[#1]%
}{%
	\endinstructionbox%
}

\def\tumexam@boxprefix@mc{100}
\newcounter{tumexam@mc}
\newif\iftumexam@mc@cross
\newenvironment{multiplechoice}{%
	\ifx\tumexam@subproblem@calc\tumexam@subproblem@calccredit%
		\ClassWarningNoLine{tumexam}{Manual multiple choice in problem \arabic{problem} \thesubproblem:
			This multiple choice problem must be evaluated manually}%
	\fi%
	\let\tumexam@mc@item\item
	\def\item{%
		\egroup%
		\stepcounter{tumexam@mc}%
		\setbox\tumexam@boxprefix@mc\twodigit{\the\c@tumexam@mc}\vtop\bgroup%
		\hsize\linewidth%
		\@ifstar{\tumexam@mc@crosstrue\tumexam@mc@item}{\tumexam@mc@crossfalse\tumexam@mc@item}%
	}%
	\renewcommand{\labelitemi}{\tikz[baseline=-0.3em]{
		\ifx\tumexam@subproblem@calc\tumexam@subproblem@calccredit
			\node[tumexam@style@cbox] at (0,0) {};
		\else
			\problemcrossbox{0}{0}{\iftumexam@mc@cross1\else0\fi}{m\arabic{tumexam@mc}}%
		\fi
		\ifsolution
			\iftumexam@mc@cross
				\begin{pgfinterruptboundingbox}
				\node at (0,0.04em) {\solution{\huge\texttimes}};
				\end{pgfinterruptboundingbox}
			\fi
		\fi
	}}%
	\setcounter{tumexam@mc}{0}%
	\partopsep=0pt%
	\itemize%
	\hrule height 0pt%
	\bgroup%
}{%
	\egroup%
	\permute{1,...,\c@tumexam@mc}[\tumexam@mc@permute]%
	\multiplechoice@i{\tumexam@mc@permute}%
}
\newenvironment{multiplechoice*}{%
	\multiplechoice
}{%
	\egroup%
	\multiplechoice@i{{1,...,\c@tumexam@mc}}%
}
\newcommand{\multiplechoice@i}[1]{%
	\foreach \x in #1 {%
		\hbox{\hskip\@totalleftmargin\box\tumexam@boxprefix@mc\twodigit{\x}}%
	}%
	\enditemize%
}


\newbox\tumexam@inlinesolutionbox
\def\solution{\@ifstar{\let\solution@ii\underbar\solution@i}{\let\solution@ii\hbox\solution@i}}
\newcommand{\solution@i}[2][]{%
	\setbox\tumexam@inlinesolutionbox\hbox{#2}%
	\if\@empty#1\@empty\else\wd\tumexam@inlinesolutionbox#1\fi%
	\ifsolution%
		\leavevmode\solution@ii{\color{blue}\box\tumexam@inlinesolutionbox}%
	\else%
		\leavevmode\solution@ii{\phantom{\box\tumexam@inlinesolutionbox}}%
	\fi%
}


% Creates a clickable textbox with optional solution
\newcounter{tumexam@textboxinputc}
\newcommand{\textboxinput}[3][\textwidth]{%
	\ifsolution%
		\textcolor{blue}{#3}%
	\else%
		\TextField[name=tumexam@textboxinput\thetumexam@textboxinputc,width=#1,height=#2,charsize=8pt,align=0,multiline=true,bordercolor=,backgroundcolor=,color=0 0.3725 0.7765]{}%
		\stepcounter{tumexam@textboxinputc}%
	\fi%
}

\newcommand{\correction}[1]{%
	\ifcorrection%
		\begingroup%
			\color{red}%
			#1%
		\endgroup%
	\fi%
}


\newcommand{\tumexam@externalpdf@problem}[1]{%
	\csvreader[head to column names,separator=semicolon]{#1/problem-\AM@page.csv}{}{%
		\if t\start%
			\problem{}%
		\fi%
		\vspace*{\ypos\textheight}%
		\refstepcounter{subproblem}%
		\subproblem@ii{\credit}%
	}%
}

\newcommand{\externalpdf}[1]{
	\begingroup
	\noproblemtrue
	\includepdf[pages=-,pagecommand={\tumexam@externalpdf@problem{#1}}]{#1/template.pdf}
	\endgroup
	\makespacealign*
}


\newlength{\tumexam@spaceleft}
\newcommand{\makespace}[2][1]{%
	\foreach \x in {1,...,#1} {%
		\vskip\baselineskip%
		\vbox {}%
		\vskip-1em%
		\vskip-\baselineskip%
		\vbox {}%
		\vskip-1ex%
		\setlength{\tumexam@spaceleft}{\textheight}%
		\addtolength{\tumexam@spaceleft}{-\pagetotal}%
		\addtolength{\tumexam@spaceleft}{-2pt}%
		\begin{#2}[\tumexam@spaceleft]
		\end{#2}%
		\newpage%
	}%
}

\newcommand{\makespacealign}[1][1]{%
	\@ifstar{\makespacealign@i{solutionbox}}{\makespacealign@i{gridsolutionbox}}%
}

\newcommand{\makespacealign@i}[2][1]{%
	\makespace[#1]{#2}%
	\ifsingleside\else%
		\if@twocolumn%
			\if@firstcolumn\else%
				\makespace{#2}%
			\fi%
		\fi%
		\ifodd\c@page%
		\else%
			\makespace{#2}%
			\if@twocolumn%
				\makespace{#2}%
			\fi%
		\fi%
	\fi%
	\iftumexam@booklet%
		\tumexam@dpage\c@page%
		\@ifundefined{AddToHook}{}{%
			\advance\tumexam@dpage -1%
		}%
		% If we use a cover sheet, the first and last two pages will be the
		% cover. So, we actually want to align the space here offset by
		% 2 so that we don't generate unnecessary empty pages for the
		% coversheet at the end.
		\ifcoversheet
			\advance\tumexam@dpage -2%
		\fi
		\divide\tumexam@dpage 2%
		\tumexam@dpage\tumexam@dpage%
		\ifodd\tumexam@dpage%
			\ifsingleside%
				\makespace[1]{#2}%
			\else%
				\makespace[2]{#2}%
				\if@twocolumn%
					\makespace[2]{#2}%
				\fi%
			\fi%
		\fi%
	\fi%
}

\newcommand{\backcover}{%
	\newcounter{tumexam@backcover@page}%
	\setcounter{tumexam@backcover@page}{\thetumexam@displaypage}%
	% We assume that the last problem has a \newpage at the end, so in the
	% new latex versions the hook to increment the counter was executed for
	% that page. In that case, we need to decrement it by one first.
	\@ifundefined{AddToHook}{}{\addtocounter{tumexam@backcover@page}{-1}}%
	% This overrides the default value that counts all pages
	\AtEndDocument{\immediate\write\@auxout{\global\c@tumexam@totalpages \thetumexam@backcover@page\relax}}
	\ifcoversheet%
		\pagestyle{tumexam@empty}%
		\null%
		\iftumexam@booklet%
			\clearquadpage%
		\else%
			\cleardoublepage%
		\fi%
	\else%
		\ifsingleside\else%
			\iftumexam@booklet%
				\clearquadpage%
			\else%
				\cleardoublepage%
			\fi%
		\fi%
	\fi%
}


\newcommand{\tumexam@makecutmarks}{%
	\begin{tikzpicture}[remember picture,overlay]
	\iftumexam@booklet
		\ifodd\value{page}
			\coordinate (a) at (current page.south west);
			\coordinate (b) at (current page.north west);
			\coordinate (offset) at (.7,0);
			\def\tumexam@cutmarklabelcoords{0.3333,0.6667}
		\else
			\coordinate (a) at (current page.south east);
			\coordinate (b) at (current page.north east);
			\coordinate (offset) at (-.7,0);
			\def\tumexam@cutmarklabelcoords{0.1667,0.5,0.8333}
		\fi
		\draw[black!20,line width=7mm,dotted] ($(a)+0.5*(offset)$) -- ($(b)+0.5*(offset)$);
		\draw[black!20,line width=1pt,dashed] ($(a)+1.5*(offset)$) -- ($(b)+1.5*(offset)$);
		\foreach \y in {3,7,...,34} {
			\node[rotate=90,font=\large] at ($(a)+(0.02,\y)+1.5*(offset)$) {\ding{34}};
		}
		\foreach \y in \tumexam@cutmarklabelcoords {
		\node[rotate=90,font=\footnotesize] at
			($(a)+0.5*(offset)+(0,\y*\paperheight)$) {\textit{\tumexam@pid}};
		}
	\else
		\ifodd\value{page}
			\coordinate (a) at ($(current page.north west)+(0,-2)$);
			\coordinate (b) at ($(current page.north west)+(2,0)$);
			\coordinate (c) at (current page.north west);
			\coordinate (offset) at (-.2,.2);
			\def\scissors@rotation{45}
			\def\scissors@xshift{0.2}
			\def\scissors@yshift{-0.2}
		\else
			\coordinate (a) at ($(current page.north east)+(0,-2)$);
			\coordinate (b) at ($(current page.north east)+(-2,0)$);
			\coordinate (c) at (current page.north east);
			\coordinate (offset) at (.2,.2);
			\def\scissors@rotation{-225}
			\def\scissors@xshift{0.2}
			\def\scissors@yshift{0.2}
		\fi
		\fill[black!20,line width=7mm,dotted,line width=1pt]
			($(a)+0.5*(offset)$) -- ($(b)+0.5*(offset)$) -- (c);
		\draw[black,dashed] (a) -- (b);
		\foreach \i in {2,5,9} {
			\path (a) --
				node[%
					yshift=\scissors@yshift,%
					xshift=\scissors@xshift,%
					rotate=\scissors@rotation,%
					pos=0.\i%
				] {\ding{34}} (b);
		}
	\fi
	\end{tikzpicture}%
}

\newcommand{\tumexam@makewatermark}{%
	\vbox to 0pt {%
		\@ifundefined{AddToHook}{%
			\vskip -1in%
			\hskip -1in%
		}\relax%
		\vbox to \paperheight {%
			\vfill%
			\hbox to 0pt {%
				\hbox to \paperwidth {%
					\hfill%
					\rotatebox{45}{%
						\fontsize{80}{80}\selectfont%
						\bfseries%
						\ifsolution%
							\color{blue!20}%
							\samplesolutionname%
						\fi%
						\ifexample
							\color{black!20}%
							\examplename%
						\fi%
					}%
					\hfill%
				}%
				\hskip 0pt minus 1 fill%
				\ifcorrection
					\hbox to \paperwidth {%
						\hfill%
						\rotatebox{45}{%
							\fontsize{40}{40}\selectfont%
							\bfseries%
							\color{red!20}%
							\correctionnotesname%
						}%
						\hfill%
					}%
					\hskip 0pt minus 1 fill%
				\fi
			}%
			\vfill%
		}%
		\vskip 0pt minus 1fill%
	}%
}
\ifsolution
	\@ifundefined{AddToHook}{%
		\AddEverypageHook{\tumexam@makewatermark}
	}{%
		\AddToHook{shipout/background}{\tumexam@makewatermark}
	}
\fi
\ifexample
	\@ifundefined{AddToHook}{%
		\AddEverypageHook{\tumexam@makewatermark}
	}{%
		\AddToHook{shipout/background}{\tumexam@makewatermark}
	}
\fi


\newcommand{\credit}{\ifcorrection\text{\textcolor{red}{\LARGE \checkmark}}\else\leavevmode\unskip\ignorespaces\fi}
\newcommand{\hcredit}{\ifcorrection\text{\textcolor{red}{\large \checkmark}}\else\leavevmode\unskip\ignorespaces\fi}


% Macros to extract random items from lists
\gdef\@randomizedValuesMacro{\tumexam@erid}
\AtEndDocument{\typeout{Randomized values CSV row: \@randomizedValuesMacro}}
\def\randitemlog#1{%
    \xdef\@randomizedValuesMacro{\@randomizedValuesMacro,#1}%
}
\def\randitem#1#2{%
    \expandafter\pgfmathrandomitem\expandafter{\csname\expandafter\@gobble\string#1uncolored\endcsname}{#2}%
    \expandafter\edef\csname\expandafter\@gobble\string#1uncolored\endcsname{\csname\expandafter\@gobble\string#1uncolored\endcsname}%
    \expandafter\randitemlog\expandafter{\csname\expandafter\@gobble\string#1uncolored\endcsname}%
    \def#1{{\ifcorrection\color{red}\fi\csname\expandafter\@gobble\string#1uncolored\endcsname}}%
}
\def\randitemsameindex#1#2{%
    \expandafter\edef\csname\expandafter\@gobble\string#1uncolored\endcsname{%
        \expandafter\noexpand\csname pgfmath@randomlist@#2@\pgfmath@randomtemp\endcsname%
    }%
    \expandafter\randitemlog\expandafter{\csname\expandafter\@gobble\string#1uncolored\endcsname}%
    \def#1{{\ifcorrection\color{red}\fi\csname \expandafter\@gobble\string#1uncolored\endcsname}}%
}
\def\randinteger#1#2#3{%
    \expandafter\pgfmathrandominteger\csname\expandafter\@gobble\string#1uncolored\endcsname{#2}{#3}%
    \expandafter\randitemlog\expandafter{\csname\expandafter\@gobble\string#1uncolored\endcsname}%
    \def#1{{\ifcorrection\color{red}\fi\csname\expandafter\@gobble\string#1uncolored\endcsname}}%
}


\endinput
