"""Independent monthly delivery checks and rejection of inconsistent exports."""
import importlib.util
from pathlib import Path

import pandas as pd
import pytest

from beyond_beta.cli import analyze
from beyond_beta.config import load_config

SPEC = importlib.util.spec_from_file_location(
    'verify_delivery', Path(__file__).resolve().parents[1] / 'scripts/verify_delivery.py',
)
delivery = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(delivery)


def test_delivery_recalculates_synthetic_export_without_daily_inputs(synthetic_project):
    root, _, path = synthetic_project
    analyze(load_config(path))
    # The review command must work from the delivered monthly workbook and tables.
    import shutil
    shutil.rmtree(root / 'data')
    result = delivery.verify(root)
    assert result['months'] == 24
    assert result['regressions'] == 4
    assert result['max_absolute_difference'] < 1e-10


@pytest.mark.parametrize('table,field', [('returns_usd', 'Sintético A'), ('capm', 'coefficient')])
def test_delivery_rejects_changed_return_or_coefficient(synthetic_project, table, field):
    root, _, path = synthetic_project
    analyze(load_config(path))
    output = root / f'reports/tables/{table}.csv'
    frame = pd.read_csv(output)
    frame.loc[0, field] += .01
    frame.to_csv(output, index=False)
    with pytest.raises(ValueError, match='diferencia máxima'):
        delivery.verify(root)
