"""Fuentes LaTeX y compilación local reproducible con XeLaTeX."""
from pathlib import Path
import os
import re
import shutil
import subprocess

MATH_TEXT={
 'R_i,t - RF_t = alfa_i + beta_i*(Mkt-RF)_t + error_i,t':r'R_{i,t}-\mathrm{RF}_t=\alpha_i+\beta_i(\mathrm{Mkt-RF})_t+\varepsilon_{i,t}',
 'R_p - RF = alfa_p + beta_m*(Mkt-RF) + beta_s*SMB + beta_h*HML + error':r'R_p-\mathrm{RF}=\alpha_p+\beta_m(\mathrm{Mkt-RF})+\beta_s\mathrm{SMB}+\beta_h\mathrm{HML}+\varepsilon',
 'R_p-RF = alfa + beta_m*(Mkt-RF) + beta_s*SMB + beta_h*HML + error':r'R_p-\mathrm{RF}=\alpha+\beta_m(\mathrm{Mkt-RF})+\beta_s\mathrm{SMB}+\beta_h\mathrm{HML}+\varepsilon',
 'R_i-RF = alfa_i + beta_i*(Mkt-RF) + error_i':r'R_i-\mathrm{RF}=\alpha_i+\beta_i(\mathrm{Mkt-RF})+\varepsilon_i',
 'R_i-RF = alfa + beta*(Mkt-RF)+error':r'R_i-\mathrm{RF}=\alpha+\beta(\mathrm{Mkt-RF})+\varepsilon',
 'producto(1+R)^(12/T)-1':r'\left[\prod_{t=1}^{T}(1+R_t)\right]^{12/T}-1',
 'producto(1+R)-1':r'\prod_{t=1}^{T}(1+R_t)-1',
 'R_USD = (1+R_EUR)*(X_t/X_(t-1))-1':r'R_{\mathrm{USD},t}=(1+R_{\mathrm{EUR},t})\frac{X_t}{X_{t-1}}-1',
 'R_t = P_t/P_(t-1)-1':r'R_t=\frac{P_t}{P_{t-1}}-1',
 'R_t = P_t/P_(t-1) - 1':r'R_t=\frac{P_t}{P_{t-1}}-1',
 'P_USD = P_EUR * X':r'P_{\mathrm{USD}}=P_{\mathrm{EUR}}X',
 'R_p,t = suma(w_i*R_i,t)':r'R_{p,t}=\sum_i w_i R_{i,t}',
 'R_p = suma(w_i*R_i), w_i>0':r'R_p=\sum_iw_iR_i,\quad w_i>0',
 'CAGR = riqueza_final^(12/T)-1':r'\mathrm{CAGR}=G_T^{12/T}-1',
 'sqrt(12)':r'\sqrt{12}',
}


def tex_escape(text):
    replacements={'\\':r'\textbackslash{}','&':r'\&','%':r'\%','$':r'\$','#':r'\#','_':r'\_',
                  '{':r'\{','}':r'\}','~':r'\textasciitilde{}','^':r'\textasciicircum{}',
                  '²':r'\textsuperscript{2}','×':r'\(\times\)','−':'-','–':'--','—':'---'}
    return ''.join(replacements.get(char,char) for char in str(text))


def inline(text):
    """URLs y hashes se dejan partir; los caracteres de texto se escapan."""
    math_pattern='|'.join(re.escape(value) for value in sorted(MATH_TEXT,key=len,reverse=True))
    parts=re.split(r'(https?://[^\s]+|\b[a-f0-9]{64}\b|\b[a-f0-9]{32}\b|\b\d{4}-\d{2}-\d{2}T[0-9:.+\-]+|'+math_pattern+')',str(text))
    rendered=[]
    for part in parts:
        if part in MATH_TEXT:rendered.append(r'\('+MATH_TEXT[part]+r'\)')
        elif part.startswith(('https://','http://')):
            suffix='.' if part.endswith('.') else ''
            rendered.append(r'\url{'+part.rstrip('.')+'}'+suffix)
        elif re.fullmatch(r'[a-f0-9]{32}|[a-f0-9]{64}|\d{4}-\d{2}-\d{2}T[0-9:.+\-]+',part):
            rendered.append(r'\nolinkurl{'+part+'}')
        else:rendered.append(tex_escape(part))
    return ''.join(rendered)


def find_engine():
    explicit=os.environ.get('BEYOND_BETA_XELATEX')
    candidates=[explicit,shutil.which('xelatex')]
    for key in ['LOCALAPPDATA','ProgramFiles']:
        base=os.environ.get(key)
        if base:
            candidates.append(str(Path(base)/('Programs/MiKTeX' if key=='LOCALAPPDATA' else 'MiKTeX')/'miktex/bin/x64/xelatex.exe'))
    for candidate in candidates:
        if candidate and Path(candidate).is_file():return str(Path(candidate))
    raise FileNotFoundError('No se encuentra XeLaTeX. Instala MiKTeX o define BEYOND_BETA_XELATEX con la ruta del ejecutable.')


def compile_tex(path):
    path=Path(path).resolve();engine=find_engine()
    pdf=path.with_suffix('.pdf')
    # Preserve the previous layout once before replacing it.
    archive=path.parent/'archive'/f'{path.stem}_anterior.pdf'
    if pdf.exists() and not archive.exists():
        archive.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(pdf,archive)
    # Contents, figure/table lists and cross-references need stable auxiliary files.
    for number in [1,2,3]:
        result=subprocess.run([engine,'-no-shell-escape','-interaction=nonstopmode','-halt-on-error','-file-line-error',path.name],
                              cwd=path.parent,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=180)
        path.with_name(f'{path.stem}.compile.{number}.log').write_text(result.stdout+'\n'+result.stderr,encoding='utf-8')
        if result.returncode or not pdf.exists():
            raise RuntimeError(f'Falló XeLaTeX en {path.name}:\n'+ '\n'.join(result.stdout.splitlines()[-25:]))
    return pdf


def table_latex(headers, rows, widths=None):
    count=len(headers)
    if widths:
        total=sum(widths)
        spec=''.join(('L' if j==0 or headers[0]=='Activo' and headers[-1]=='Peso' else 'R')+r'{\dimexpr '+f'{width/total:.5f}'+r'\linewidth-2\tabcolsep\relax}' for j,width in enumerate(widths))
    else:spec='Y'*count
    environment='tabular' if widths else 'tabularx'
    start=r'\begin{tabular}{'+spec+'}' if widths else r'\begin{tabularx}{\linewidth}{'+spec+'}'
    body=[r'\begingroup\small',start,r'\toprule',r'\rowcolor{light} '+' & '.join(r'\textbf{'+inline('Coef.' if h=='Coeficiente' else h)+'}' for h in headers)+r' \\',r'\midrule']
    for row in rows:
        if row[0] == 'Cartera': body.append(r'\midrule')
        body.append(' & '.join(inline(value) for value in row)+r' \\')
    body.extend([r'\bottomrule',r'\end{'+environment+'}',r'\endgroup',r'\par\medskip'])
    return '\n'.join(body)


EQUATIONS={
 'Datos y decisión de moneda':r'P^{\mathrm{USD}}_{i,t}=P^{\mathrm{EUR}}_{i,t}X_{i,t},\qquad X_{i,t}=\text{USD por EUR en la fecha usada para el activo }i.',
 'Resultados descriptivos':r'R_{i,t}=\frac{P_{i,t}}{P_{i,t-1}}-1,\qquad G_i=\prod_{t=1}^{T}(1+R_{i,t}),\qquad \mathrm{CAGR}_i=G_i^{12/T}-1.',
 'SML estimada con medias históricas':r'\overline R_i^{\mathrm{SML}}=\overline{\mathrm{RF}}+\widehat\beta_i\,\overline{\mathrm{Mkt-RF}},\qquad \overline R_i-\overline R_i^{\mathrm{SML}}=\widehat\alpha_i.',
 'Cartera y Fama–French de tres factores':r'R_{p,t}-\mathrm{RF}_t=\alpha_p+\beta_m(\mathrm{Mkt-RF})_t+\beta_s\,\mathrm{SMB}_t+\beta_h\,\mathrm{HML}_t+\varepsilon_{p,t}.',
}


def preamble(root,title):
    text=(Path(root)/'templates/latex/preamble.tex').read_text(encoding='utf-8')
    return text+'\n'+r'\hypersetup{pdftitle={'+tex_escape(title)+r'},pdfauthor={Alonso Castro Freibott, Pablo Caonabo Crespo de la Cruz, Carlos Segovia Domínguez y Jaime Blanco González}}'+'\n'+r'\begin{document}'+'\n'+r'{\LARGE\sffamily\bfseries\color{ink}'+tex_escape(title)+r'\par}\medskip'+'\n'+r'{\small Alonso Castro Freibott, Pablo Caonabo Crespo de la Cruz, Carlos Segovia Domínguez y Jaime Blanco González\par}\medskip'+'\n'


def format_report_source(root, source, subtitle):
    """Apply academic layout to generated content without recalculating results."""
    if '% ACADEMIC_FRONTMATTER' in source:
        return source
    document = source.split(r'\begin{document}', 1)[1].rsplit(r'\end{document}', 1)[0]
    start = document.find('Comparamos la rentabilidad')
    if start < 0:
        raise ValueError('No se reconoce el inicio del contenido del informe')
    document = document[start:]
    # Move detailed coefficients to an actual appendix after the main discussion.
    sections = re.split(r'(?=\\section\{)', document)
    appendix_titles = ('Anexo de coeficientes CAPM', 'Sensibilidad de la inferencia')
    appendix = [next(section for section in sections if section.startswith(r'\section{' + title + '}'))
                for title in appendix_titles]
    sections = [section for section in sections if section not in appendix]
    document = ''.join(sections).rstrip()
    document = re.sub(r'\\clearpage\s*$', '', document)
    annex = appendix[0].rstrip().replace(
        r'\section{Anexo de coeficientes CAPM}', r'\section{Resultados completos del CAPM}', 1
    )
    annex += '\n' + r'\clearpage' + '\n' + appendix[1].strip()
    document += '\n\\clearpage\n\\appendix\n' + annex
    front = r'''
% ACADEMIC_FRONTMATTER
\hypersetup{pdftitle={Beyond Beta: el CAPM y los modelos multifactoriales en la práctica},
pdfauthor={Alonso Castro Freibott, Pablo Caonabo Crespo de la Cruz, Carlos Segovia Domínguez y Jaime Blanco González},
pdfsubject={Informe académico de Inversiones Financieras},pdfkeywords={CAPM, Fama-French, cartera, rentabilidad, riesgo}}
\begin{document}
\pagenumbering{gobble}
\begin{titlepage}
\thispagestyle{empty}
\vspace*{12mm}
{\sffamily\bfseries\color{ink}CUNEF Universidad\par}
\vspace{4mm}
{\sffamily\normalsize Inversiones Financieras\par}
\vspace{20mm}
{\sffamily\bfseries\fontsize{38}{44}\selectfont\color{ink}Beyond Beta\par}
\vspace{7mm}
{\sffamily\Large\color{ink}El CAPM y los modelos\par multifactoriales en la práctica\par}
\vspace{5mm}
{\large Informe académico\par}
\vspace{9mm}
{\color{ink}\rule{\linewidth}{0.8pt}\par}
\vspace{8mm}
\colorbox{light}{\parbox{\dimexpr\linewidth-2\fboxsep\relax}{\vspace{4mm}\hspace{3mm}\textbf{Periodo de análisis y moneda}\\[2mm]\hspace{3mm}@@SUBTITLE@@\vspace{4mm}}}\par
\vspace{8mm}
{\sffamily\bfseries\color{ink}Autores\par}\vspace{2mm}
Alonso Castro Freibott\\
Pablo Caonabo Crespo de la Cruz\\
Carlos Segovia Domínguez\\
Jaime Blanco González\par
\vspace{7mm}
{\sffamily\bfseries\color{ink}Profesor\par}
Javier Fernández Sánchez de la Viña\par
\vfill
{\small Curso académico 2026--2027\hfill Noviembre de 2026\par}
\end{titlepage}
\pagenumbering{roman}
\setcounter{tocdepth}{2}
\renewcommand{\contentsname}{Índice de contenidos}
\renewcommand{\listfigurename}{Índice de figuras}
\renewcommand{\listtablename}{Índice de tablas}
\renewcommand{\tablename}{Tabla}
\tableofcontents
\clearpage
\phantomsection
\addcontentsline{toc}{section}{Índice de figuras}
\listoffigures
\vspace{10mm}
\phantomsection
\addcontentsline{toc}{section}{Índice de tablas}
\listoftables
\clearpage
\pagenumbering{arabic}
\section{Resumen ejecutivo}
'''.replace('@@SUBTITLE@@', inline(subtitle))
    return (Path(root) / 'templates/latex/preamble.tex').read_text(encoding='utf-8') + '\n' + front + document + '\n\\end{document}\n'


def write_report(root,blocks,directory,subtitle="",compile_pdf=True):
    title=blocks[0][1];body=[preamble(root,title),r'{\small '+inline(subtitle)+r'\par}\bigskip']
    references=False
    for index,(kind,data) in enumerate(blocks):
        if index==0:continue
        if kind=='page':continue
        elif kind=='heading':
            level='subsection' if data in {'Diversificación y contraste en euros','SML estimada con medias históricas','Rentabilidad y volatilidad'} else 'section'
            reserved_lines = 14 if data == 'Referencias y fuentes' else 7
            body.append(rf'\Needspace{{{reserved_lines}\baselineskip}}' + chr(92)+level+'{'+inline(data)+'}')
            if data=='Referencias y fuentes':body.append(r'\begingroup\small\setlength{\parskip}{4pt}');references=True
            if data in EQUATIONS:body.extend([r'\begin{equation*}',EQUATIONS[data],r'\end{equation*}'])
        elif kind=='paragraph':body.append(inline(data)+'\n')
        elif kind=='latex':body.append(data.replace(r'\begin{thebibliography}{9}',r'\begingroup\renewcommand{\section}[2]{}\begin{thebibliography}{9}').replace(r'\end{thebibliography}',r'\end{thebibliography}\endgroup'))
        elif kind=='table':
            headers,rows,widths,key,title=data
            body.extend([r'\par\noindent\begin{minipage}{\linewidth}',r'\captionof{table}['+inline(title)+']{'+inline(title)+'}',r'\label{tab:'+key+'}',table_latex(headers,rows,widths),r'\end{minipage}\par\medskip'])
        elif kind=='figure':
            name,caption,width=data
            key=Path(name).stem.replace('_usd','')
            short={'wealth':'Riqueza acumulada','correlations':'Correlaciones mensuales','sml':'SML histórica','risk_return':'Rentabilidad y volatilidad','capm_scatter':'Regresiones CAPM por activo'}[key]
            caption=re.sub(r'^Figura \d+\.\s*','',caption)
            fraction=min(width/490,1)
            body.extend([r'\par\begin{figure}[!htbp]\centering',r'\includegraphics[width='+f'{fraction:.3f}'+r'\linewidth,keepaspectratio]{../figures/'+name+'}',r'\captionof{figure}['+short+']{'+inline(caption)+'}',r'\label{fig:'+key+'}',r'\end{figure}\par'])
    if references:body.append(r'\endgroup')
    body.append(r'\end{document}')
    path=Path(directory)/'informe.tex'
    path.write_text(format_report_source(root, '\n'.join(body), subtitle), encoding='utf-8')
    return compile_tex(path) if compile_pdf else path


def markdown_inline(text):
    parts=re.split(r'(\*\*[^*]+\*\*|`[^`]+`)',text)
    return ''.join(r'\textbf{'+inline(p[2:-2])+'}' if p.startswith('**') else r'\texttt{'+inline(p[1:-1])+'}' if p.startswith('`') else inline(p) for p in parts)


def write_markdown_document(root,source,output,title,compile_pdf=True):
    lines=Path(source).read_text(encoding='utf-8').splitlines();body=[preamble(root,title)]
    i=0;in_list=False;title_seen=False
    while i<len(lines):
        line=lines[i].strip()
        if not line:
            if in_list:body.append(r'\end{itemize}');in_list=False
            body.append('');i+=1;continue
        if line.startswith('# '):
            if title_seen:body.append(r'\section{'+inline(line[2:])+'}')
            title_seen=True;i+=1;continue
        if line.startswith('## '):body.append(r'\section{'+inline(line[3:])+'}');i+=1;continue
        if line.startswith('### '):body.append(r'\subsection*{'+inline(line[4:])+'}');i+=1;continue
        if line.startswith('|'):
            rows=[]
            while i<len(lines) and lines[i].strip().startswith('|'):
                row=[cell.strip() for cell in lines[i].strip().strip('|').split('|')]
                if not all(re.fullmatch(r'[-: ]+',cell) for cell in row):rows.append(row)
                i+=1
            body.append(table_latex(rows[0],rows[1:]));continue
        if line.startswith('- '):
            if not in_list:body.append(r'\begin{itemize}');in_list=True
            body.append(r'\item '+markdown_inline(line[2:]));i+=1;continue
        paragraph=[line];i+=1
        while i<len(lines) and lines[i].strip() and not lines[i].startswith(('#','|','- ')):
            paragraph.append(lines[i].strip());i+=1
        text=' '.join(paragraph)
        if text.startswith('Rentabilidad acumulada = producto(1+R)-1.'):
            body.extend([r'\begin{align*}',r'G_T&=\prod_{t=1}^{T}(1+R_t), & R_{\mathrm{acum}}&=G_T-1, & \mathrm{CAGR}&=G_T^{12/T}-1.',r'\end{align*}'])
            text=text.split('Media mensual =',1)[-1]
            text='Media mensual ='+text
        body.append(markdown_inline(text)+'\n')
    if in_list:body.append(r'\end{itemize}')
    body.append(r'\end{document}')
    output=Path(output);output.write_text('\n'.join(body),encoding='utf-8')
    return compile_tex(output) if compile_pdf else output
