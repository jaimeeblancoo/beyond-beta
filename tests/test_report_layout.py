"""Academic document structure, independent of the local TeX installation."""
from beyond_beta.cli import analyze
from beyond_beta.config import load_config
from beyond_beta.report import generate_report


def test_report_has_cover_navigation_and_appendix(synthetic_project):
    root, _, path = synthetic_project
    config = load_config(path)
    analyze(config)
    generate_report(config, compile_pdf=False)
    source = (root / 'reports/report/informe.tex').read_text(encoding='utf-8')
    assert r'\begin{titlepage}' in source and r'\thispagestyle{empty}' in source
    for command in [r'\tableofcontents', r'\listoffigures', r'\listoftables']:
        assert command in source
    assert r'\pagenumbering{roman}' in source and r'\pagenumbering{arabic}' in source
    assert source.count(r'\captionof{table}') == 9
    assert source.count(r'\captionof{figure}') == 5
    assert source.index(r'\section{Referencias y fuentes}') < source.index(r'\appendix')
    assert not (root / 'reports/report/guia_defensa.md').exists()

    assert r'\label{tab:capm}' in source
    assert r'\ref{tab:capm}' in source
    assert r'\label{fig:sml}' in source
    assert r'\cite{sharpe}' in source
    assert source.index(r'\appendix') < source.index(r'\section{Sensibilidad de la inferencia}')
    assert source.count(r'\clearpage') == 4
