from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FINAL_BOOK_DIR = ROOT / "Final Book"
DEFAULT_OUTPUT = FINAL_BOOK_DIR / "main.tex"

@dataclass(frozen=True)
class SourceBook:
    folder: str
    title: str

BOOKS = (
    SourceBook("Domestic data entry operator-9th", "Domestic Data Entry Operator"),
    SourceBook("Domestic data entry operator-10th", "Domestic Data Entry Operator"),
    SourceBook("Web developer-11th", "Web Development"),
    SourceBook("Web developer-12th", "Web Development"),
    SourceBook("Artificial intelligence assistant-9th", "Artificial Intelligence"),
    SourceBook("Artificial intelligence assistant-10th", "Artificial Intelligence"),
    SourceBook("Junior software developer-11th", "Junior Software Development"),
    SourceBook("Junior software developer-12th", "Junior Software Development"),
)

def source_tex(book: SourceBook) -> Path:
    path = ROOT / book.folder / "main.tex"
    if not path.is_file():
        raise FileNotFoundError(f"Missing source LaTeX file: {path}")
    return path

def extract_body(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    start = text.find(r"\mainmatter")
    if start >= 0:
        text = text[start + len(r"\mainmatter"):]
    else:
        start = text.find(r"\begin{document}")
        if start < 0:
            raise ValueError(f"No document body found in {path}")
        text = text[start + len(r"\begin{document}"):]
    # Remove per-book back matter and document terminators.
    text = re.split(r"\\backmatter\b|\\end\{document\}", text, maxsplit=1)[0]
    text = re.sub(r"\\frontmatter\b|\\mainmatter\b|\\tableofcontents\b", "", text)
    text = re.sub(r"(?m)^\s*\\appendix\s*$", "", text)
    # Strip all source-level page styles/marks so no original book headers or footers leak into the combined volume.
    text = re.sub(r"\\thispagestyle\{[^}]*\}|\\pagestyle\{[^}]*\}", "", text)
    text = re.sub(r"\\markboth\{[^{}]*\}\{[^{}]*\}|\\markright\{[^{}]*\}", "", text)
    text = re.sub(r"\\fancy(?:head|foot)\s*(?:\[[^]]*\])?\s*\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", "", text)
    # Rewrite every source-book asset path (including \IfFileExists guards) to the
    # copied, space-free assets/bookN tree. This prevents false "illustration unavailable"
    # messages when the image exists in the repository/build workspace.
    book_index = next(i for i, item in enumerate(BOOKS, start=1) if item.folder == path.parent.name)
    source_prefix = re.escape("../" + path.parent.name + "/")
    text = re.sub(source_prefix, f"assets/book{book_index}/", text)
    # Source books also use paths relative to their own folder. Redirect these too.\n    text = re.sub(r"(?<![A-Za-z0-9_./-])(images|book_illustrations)/", rf"assets/book{book_index}/\\g<1>/", text)\n    # Keep photos and diagrams inside the page's vertical text area to prevent overlap.
    def constrain_image(match: re.Match[str]) -> str:
        options = match.group(1) or ""
        image_path = match.group(2)
        if not re.search(r"\bheight\s*=", options):
            options = options.strip("[]")
            options = (options + "," if options else "") + r"height=55mm,keepaspectratio"
            options = "[" + options + "]"
        return r"\includegraphics" + options + "{" + image_path + "}"
    text = re.sub(r"\\includegraphics(\[[^\]]*\])?\{([^{}]+)\}", constrain_image, text)
    # Missing optional source illustrations must not abort the entire textbook build.
    # Keep every valid image; show a small fallback only when a referenced file is absent.
    def guard_image(match: re.Match[str]) -> str:
        options = match.group(1) or ""
        image_path = match.group(2)
        original = f"\\includegraphics{options}{{{image_path}}}"
        return f"\\IfFileExists{{{image_path}}}{{{original}}}{{\\relax}}"
    text = re.sub(r"\\includegraphics(\[[^\]]*\])?\{([^{}]+)\}", guard_image, text)
    # Older source books may use raw LaTeX \input{...} or \include{...}; keep these
    # untouched unless those files exist in the merged directory, to avoid fatal missing-file errors.
    text = re.sub(r"\\input\{([^{}]+)\}", lambda m: m.group(0) if (FINAL_BOOK_DIR / m.group(1)).exists() else "% omitted missing input " + m.group(1), text)
    text = re.sub(r"\\include\{([^{}]+)\}", lambda m: m.group(0) if (FINAL_BOOK_DIR / (m.group(1) + ".tex")).exists() else "% omitted missing include " + m.group(1), text)
    # Normalise code listings from independently authored curricula. Unknown source styles
    # and language names can stop XeLaTeX; preserve code and general options, use plain code layout.
    def normalise_listing(match: re.Match[str]) -> str:
        options = match.group(1)
        kept = []
        for item in options.split(","):
            item = item.strip()
            if re.match(r"^(style|language)\s*=", item, flags=re.I):
                continue
            if item:
                kept.append(item)
        return r"\begin{lstlisting}" + ("[" + ",".join(kept) + "]" if kept else "")
    text = re.sub(r"\\begin\{lstlisting\}\[([^\]]*)\]", normalise_listing, text, flags=re.I)
    # Inline listings use the same safe fallback.
    text = re.sub(r"\\lstinline(?:\[[^\]]*\])?", r"\\lstinline", text)
    # The book parts are stitched together without creating separate books or cover pages.
    return text.strip()

def render_main_tex(tex_path: Path) -> str:
    bodies = []
    for index, book in enumerate(BOOKS, start=1):
        path = source_tex(book)
        body = extract_body(path)
        # Add a real, topic-relevant classroom photograph at the start of each curriculum.
        # Photos are fetched from Wikimedia Commons by the workflow and credited below.
        people_photos = {
            1: (r"assets/book1/people-photo.jpg", r"Computer-based training room photograph: Lcjuera, Wikimedia Commons, CC BY-SA 4.0."),
            2: (r"assets/book2/people-photo.jpg", r"Computer education class photograph: Yann Forget, Wikimedia Commons, CC BY-SA 2.5."),
            3: (r"assets/book3/people-photo.jpg", r"Students learning programming in Bengaluru: Nayakyashraj, Wikimedia Commons, CC BY-SA 4.0."),
            4: (r"assets/book4/people-photo.jpg", r"Teacher and students in a training session: Dr. Balkrishna Hari Mali, Wikimedia Commons, CC BY-SA 4.0."),
            5: (r"assets/book5/people-photo.jpg", r"Students learning programming in Bengaluru: Nayakyashraj, Wikimedia Commons, CC BY-SA 4.0."),
            6: (r"assets/book6/people-photo.jpg", r"Teacher and students in a training session: Dr. Balkrishna Hari Mali, Wikimedia Commons, CC BY-SA 4.0."),
            7: (r"assets/book7/people-photo.jpg", r"Computer-based training room photograph: Lcjuera, Wikimedia Commons, CC BY-SA 4.0."),
            8: (r"assets/book8/people-photo.jpg", r"Computer education class photograph: Yann Forget, Wikimedia Commons, CC BY-SA 2.5."),
        }
        photo_path, photo_credit = people_photos[index]
        photo_block = (
            "\n\\begin{center}\\includegraphics[width=.82\\textwidth,height=48mm,keepaspectratio]{"
            + photo_path + "}\\par{\\footnotesize\\textit{" + photo_credit
            + "}}\\end{center}\n"
        )
        # Place the photograph after the first chapter heading, not on a separate page.
        body = re.sub(r"(\\chapter(?:\\*?)\\s*\\{[^{}]*\\})", lambda match: match.group(1) + photo_block, body, count=1)
        # Keep the source chapter text and illustrations; only mark transitions between source curricula.
        bodies.append(
            "\n% ============================================================\n"
            f"% Curriculum sequence {index}: {book.title}\n"
            "% ============================================================\n"
            + body
        )

    body_text = "\n\n".join(bodies)
    return r"""\documentclass[11pt,openany,oneside]{book}
\usepackage[a4paper,top=25mm,bottom=25mm,left=25mm,right=22mm,headheight=22pt,footskip=14mm]{geometry}
\usepackage{fontspec}
\setmainfont{DejaVu Serif}
\setsansfont{DejaVu Sans}
\usepackage{amssymb,xcolor,graphicx,array,booktabs,longtable,tabularx,colortbl,enumitem,tikz,tcolorbox,fancyhdr,titlesec,tocloft,hyperref,eso-pic,microtype,listings}
\lstdefinestyle{webcode}{basicstyle=\ttfamily\small,breaklines=true,showstringspaces=false,columns=fullflexible,frame=single}
\lstdefinestyle{pythoncode}{basicstyle=\ttfamily\small,breaklines=true,showstringspaces=false,columns=fullflexible,frame=single}
\lstdefinestyle{pythonstyle}{basicstyle=\ttfamily\small,breaklines=true,showstringspaces=false,columns=fullflexible,frame=single}
\lstdefinestyle{sqlcode}{basicstyle=\ttfamily\small,breaklines=true,showstringspaces=false,columns=fullflexible,frame=single}
\lstdefinestyle{htmlcode}{basicstyle=\ttfamily\small,breaklines=true,showstringspaces=false,columns=fullflexible,frame=single}
\lstdefinestyle{csscode}{basicstyle=\ttfamily\small,breaklines=true,showstringspaces=false,columns=fullflexible,frame=single}
\lstdefinestyle{js code}{basicstyle=\ttfamily\small,breaklines=true,showstringspaces=false,columns=fullflexible,frame=single}
\lstdefinestyle{code}{basicstyle=\ttfamily\small,breaklines=true,showstringspaces=false,columns=fullflexible,frame=single}
\lstdefinestyle{bashcode}{basicstyle=\ttfamily\small,breaklines=true,showstringspaces=false,columns=fullflexible,frame=single}
\lstdefinestyle{javacode}{basicstyle=\ttfamily\small,breaklines=true,showstringspaces=false,columns=fullflexible,frame=single}
\lstdefinestyle{jsoncode}{basicstyle=\ttfamily\small,breaklines=true,showstringspaces=false,columns=fullflexible,frame=single}
\lstdefinestyle{phpcode}{basicstyle=\ttfamily\small,breaklines=true,showstringspaces=false,columns=fullflexible,frame=single}
\lstdefinestyle{typescriptcode}{basicstyle=\ttfamily\small,breaklines=true,showstringspaces=false,columns=fullflexible,frame=single}
\lstdefinestyle{sqlstyle}{basicstyle=\ttfamily\small,breaklines=true,showstringspaces=false,columns=fullflexible,frame=single}
\lstdefinestyle{terminal}{basicstyle=\ttfamily\small,breaklines=true,showstringspaces=false,columns=fullflexible,frame=single}
\lstdefinelanguage{HTML}{sensitive=false,morecomment=[s]{<!--}{-->},morestring=[b]",morestring=[b]',morekeywords={html,head,title,body,div,span,p,h1,h2,h3,a,img,ul,ol,li,table,tr,td,th,form,input,button,script,style,meta,link,header,footer,section,article,nav,main}}
\lstdefinelanguage{CSS}{sensitive=false,morecomment=[s]{/*}{*/},morestring=[b]",morestring=[b]',morekeywords={color,background,display,position,margin,padding,border,width,height,font,font-size,font-family,flex,grid,justify-content,align-items,content,selector,px,rem,em,none,block,inline,solid,relative,absolute,hover,media}}
\lstdefinelanguage{JavaScript}{sensitive=false,morecomment=[l]{//},morecomment=[s]{/*}{*/},morestring=[b]",morestring=[b]',morekeywords={const,let,var,function,return,if,else,for,while,class,new,import,export,from,async,await,document,window,console,log,true,false,null,undefined}}
\lstdefinelanguage{JSON}{sensitive=false,morestring=[b]",morekeywords={true,false,null}}
\lstdefinelanguage{bash}{sensitive=false,morecomment=[l]{\#},morestring=[b]",morestring=[b]',morekeywords={cd,ls,echo,export,git,npm,node,python,pip,mkdir,cp,mv,rm,sudo,apt}}
\lstdefinelanguage{Java}{sensitive=false,morecomment=[l]{//},morecomment=[s]{/*}{*/},morestring=[b]",morekeywords={public,private,protected,class,static,void,int,double,float,boolean,String,return,new,if,else,for,while,try,catch,import,package,extends,implements}}
\lstdefinelanguage{PHP}{sensitive=false,morecomment=[l]{//},morecomment=[s]{/*}{*/},morestring=[b]",morestring=[b]',morekeywords={echo,print,function,return,if,else,foreach,while,for,class,public,private,protected,new,include,require,isset,empty}}
\lstdefinelanguage{TypeScript}{sensitive=false,morecomment=[l]{//},morecomment=[s]{/*}{*/},morestring=[b]",morestring=[b]',morekeywords={const,let,var,function,return,if,else,for,while,class,interface,type,import,export,from,async,await,true,false,null,undefined}}
\lstdefinelanguage{MongoDB}{sensitive=false,morecomment=[l]{//},morecomment=[s]{/*}{*/},morestring=[b]",morestring=[b]',morekeywords={db,find,insertOne,insertMany,updateOne,deleteOne,aggregate,createCollection,match,project,group,sort,limit}}
\usetikzlibrary{arrows.meta,positioning,shapes.geometric,calc}
\definecolor{Navy}{HTML}{17365D}
\definecolor{Teal}{HTML}{007F86}
\definecolor{Pale}{HTML}{EAF6F7}
\definecolor{Gold}{HTML}{E3A72F}
\definecolor{Ink}{HTML}{293746}
\definecolor{LightGold}{HTML}{FFF5DD}
\definecolor{SoftGray}{HTML}{F4F6F9}
\definecolor{Coral}{HTML}{D95D50}
\definecolor{Violet}{HTML}{7656A6}
\definecolor{Sky}{HTML}{DCEEFF}
\definecolor{Rose}{HTML}{FCEBE8}
\hypersetup{colorlinks=true,linkcolor=Teal,urlcolor=Teal,pdftitle={Combined Vocational Education Textbook},pdfauthor={Vocational Education}}
% Reserve enough room for three-digit chapter numbers in the single continuous contents list.
\setlength{\cftchapindent}{0em}
\setlength{\cftchapnumwidth}{4.2em}
\setlength{\cftsecindent}{1.8em}
\setlength{\cftsecnumwidth}{3.0em}
\setlength{\cftsubsecindent}{3.8em}
\setlength{\cftsubsecnumwidth}{3.6em}
\setlist[itemize]{leftmargin=1.5em,itemsep=1.5pt,topsep=2pt,parsep=0pt}
\setlist[enumerate]{leftmargin=1.7em,itemsep=2pt,topsep=2pt,parsep=0pt}
\setlength{\parindent}{0pt}
\setlength{\parskip}{3pt}
\setlength{\emergencystretch}{3em}
% Consistent navy-teal-gold page border, running header, and continuous page number.
\AddToShipoutPictureBG{\begin{tikzpicture}[remember picture,overlay]
\draw[Navy,line width=1.15pt] ([xshift=9mm,yshift=-9mm]current page.north west) rectangle ([xshift=-9mm,yshift=9mm]current page.south east);
\draw[Teal,line width=.55pt] ([xshift=11.5mm,yshift=-11.5mm]current page.north west) rectangle ([xshift=-11.5mm,yshift=11.5mm]current page.south east);
\draw[Teal,line width=2pt] ([xshift=9mm,yshift=-9mm]current page.north west)--([xshift=35mm,yshift=-9mm]current page.north west);
\draw[Coral,line width=2pt] ([xshift=-9mm,yshift=9mm]current page.south east)--([xshift=-35mm,yshift=9mm]current page.south east);
\fill[Gold] ([xshift=9mm,yshift=-9mm]current page.north west) circle (1.2mm);
\fill[Violet] ([xshift=-9mm,yshift=9mm]current page.south east) circle (1.2mm);
\end{tikzpicture}}
\pagestyle{fancy}
\fancyhf{}
% No added running headers; keep only one continuous page number throughout the volume.
\fancyfoot[C]{\small\bfseries\color{Navy}\thepage}
\renewcommand{\headrulewidth}{0pt}
\fancypagestyle{plain}{\fancyhf{}\fancyfoot[C]{\small\bfseries\color{Navy}\thepage}\renewcommand{\headrulewidth}{0pt}}
\titleformat{\chapter}[display]{\normalfont\sffamily\bfseries\color{Navy}}{\filleft\Large\color{Coral}\chaptername\ \thechapter}{.6ex}{\color{Teal}\LARGE\raggedright}
\titlespacing*{\chapter}{0pt}{-2mm}{.8ex}
\titleformat{\section}{\Large\sffamily\bfseries\color{Teal}}{\color{Coral}\thesection}{.7em}{}
\titleformat{\subsection}{\large\sffamily\bfseries\color{Violet}}{\thesubsection}{.7em}{}
\titlespacing*{\section}{0pt}{1.2ex plus .2ex minus .2ex}{.35ex}
\titlespacing*{\subsection}{0pt}{1ex plus .2ex minus .2ex}{.3ex}
\newcommand{\keyterm}[1]{\textbf{\color{Navy}#1}}
\newcommand{\checklistitem}{\noindent$\square$\quad}
\newcommand{\exampractice}[1]{\begin{tcolorbox}[colback=LightGold,colframe=Gold,boxrule=.6pt,arc=1.2mm,left=2mm,right=2mm,top=1mm,bottom=1mm]\textbf{Review questions.} #1\end{tcolorbox}}
\newenvironment{keybox}{\begin{tcolorbox}[colback=Pale,colframe=Teal,boxrule=.6pt,arc=1mm,left=2mm,right=2mm,top=1mm,bottom=1mm]}{\end{tcolorbox}}
\newenvironment{notebox}{\begin{tcolorbox}[colback=SoftGray,colframe=Navy!70,boxrule=.6pt,arc=1mm,left=2mm,right=2mm,top=1mm,bottom=1mm]}{\end{tcolorbox}}
\newenvironment{examplebox}{\begin{tcolorbox}[colback=Sky!45,colframe=Teal!80,boxrule=.6pt,arc=1mm,left=2mm,right=2mm,top=1mm,bottom=1mm]}{\end{tcolorbox}}
\newenvironment{warningbox}{\begin{tcolorbox}[colback=Rose,colframe=Coral,boxrule=.6pt,arc=1mm,left=2mm,right=2mm,top=1mm,bottom=1mm]}{\end{tcolorbox}}
\newenvironment{activitybox}{\begin{tcolorbox}[colback=LightGold,colframe=Gold,boxrule=.6pt,arc=1mm,left=2mm,right=2mm,top=1mm,bottom=1mm]}{\end{tcolorbox}}
\newcommand{\reviewtitle}{\par\noindent\textbf{\color{Navy}Review Questions}\par}
\newcommand{\review}[1]{\par\smallskip\reviewtitle\begin{enumerate}[label=\arabic*.,leftmargin=1.8em,itemsep=1pt,topsep=2pt]\small #1\end{enumerate}\smallskip}
\newcommand{\photo}[3]{\begin{center}\begin{tcolorbox}[colback=white,colframe=Teal!70,boxrule=.8pt,arc=1mm,left=2mm,right=2mm,top=2mm,bottom=2mm,width=.88\textwidth]\centering\IfFileExists{../Junior software developer-11th/images/#1}{\includegraphics[width=.92\linewidth,height=46mm,keepaspectratio]{../Junior software developer-11th/images/#1}}{\textbf{#2}}\end{tcolorbox}\end{center}{\small\textit{#3}}}
\begin{document}
\pagenumbering{arabic}
\begin{titlepage}
\thispagestyle{plain}
\centering
\vspace*{25mm}
{\Huge\bfseries VOCATIONAL EDUCATION\par}
\vspace{5mm}
{\LARGE Combined Textbook\par}
\vspace{8mm}
{\large Data Entry \textbullet\ Web Development \textbullet\ Artificial Intelligence \textbullet\ Software Development\par}
\vfill
{\large Classes IX--XII\par}
\vspace{4mm}
{\normalsize A continuous learning volume\par}
\end{titlepage}
\tableofcontents
\clearpage
""" + body_text + r"""

\end{document}
"""

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a continuous textbook from source LaTeX chapters.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()

def main() -> None:
    args = parse_args()
    output = args.output if args.output.is_absolute() else ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    text = render_main_tex(output)
    if text.count(r"\begin{document}") != 1 or text.count(r"\end{document}") != 1:
        raise SystemExit("Generated source has invalid document boundaries.")
    if r"\includepdf" in text or r"\usepackage{pdfpages}" in text:
        raise SystemExit("PDF concatenation is not allowed in the continuous-book build.")
    output.write_text(text, encoding="utf-8")
    print(f"Generated continuous textbook source: {output}")
    print(f"Included {len(BOOKS)} curriculum source bodies in order.")

if __name__ == "__main__":
    main()
