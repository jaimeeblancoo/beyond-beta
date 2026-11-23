"""Contratos financieros y procedencia de la presentación, con datos sintéticos."""
import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from beyond_beta.cli import analyze
from beyond_beta.config import load_config
from beyond_beta.report import generate_report
from beyond_beta.provenance import artifact_hashes, write_json

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('build_presentation', ROOT/'scripts/build_presentation.py')
presentation = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(presentation)


def test_sml_distance_is_monthly_alpha_not_cagr():
    index = pd.period_range('2020-01', periods=12, freq='M')
    market = np.linspace(-.04, .06, 12)
    factors = pd.DataFrame({'Mkt-RF':market,'RF':.001}, index=index)
    beta = pd.Series({'Activo A':.7,'Activo B':1.2})
    alpha = pd.Series({'Activo A':.003,'Activo B':-.002})
    returns = pd.DataFrame({name:.001+alpha[name]+beta[name]*market for name in beta.index}, index=index)
    expected, realized = presentation.sml_coordinates(returns, factors, beta)
    np.testing.assert_allclose((realized-expected).to_numpy(), alpha.to_numpy(), atol=1e-15)


def test_template_missing_value_fails_instead_of_leaving_stale_number():
    with pytest.raises(ValueError, match='Falta contenido'):
        presentation.replace_tokens('@@MISSING@@', {})
    assert presentation.replace_tokens('@@VALUE@@', {'VALUE':'5 %'}, latex=True) == r'5 \%'


def test_presentation_rejects_changed_outputs_and_inputs(synthetic_project):
    root, _, path = synthetic_project
    for name in presentation.SOURCES:
        target = root/name
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():target.write_text('Synthetic presentation source', encoding='utf-8')
    config = load_config(path)
    analyze(config); generate_report(config, compile_pdf=False)
    state = presentation.input_state(config)
    folder = root/'reports/presentation';folder.mkdir()
    output = folder/'Synthetic.pdf';output.write_bytes(b'Synthetic output only')
    manifest = {'stage':'complete','inputs':state,'outputs':artifact_hashes(root,[output.relative_to(root)])}
    write_json(folder/'presentation_manifest.json',manifest)
    presentation.validate_presentation(config)
    output.write_bytes(b'Changed output')
    with pytest.raises(ValueError,match='alterado'):presentation.validate_presentation(config)
    output.write_bytes(b'Synthetic output only')
    (root/'templates/beamer/presentation.tex').write_text('Changed presentation source',encoding='utf-8')
    with pytest.raises(ValueError,match='entradas de otra'):presentation.validate_presentation(config)
    manifest['inputs']=presentation.input_state(config);manifest['stage']='building'
    write_json(folder/'presentation_manifest.json',manifest)
    with pytest.raises(ValueError,match='incompleta'):presentation.validate_presentation(config)
