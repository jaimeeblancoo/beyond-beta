"""Lectura exclusiva del bloque mensual original de Kenneth French."""
import csv
import re
from pathlib import Path
import numpy as np
import pandas as pd

COLUMNS = ["Mkt-RF", "SMB", "HML", "RF"]

def read_factors(path):
    rows, started, ended, header_found = [], False, False, False
    for row in csv.reader(Path(path).read_text(encoding="utf-8-sig").splitlines()):
        key = row[0].strip() if row else ""
        if [v.strip() for v in row[1:]] == COLUMNS:
            header_found = True
        if re.fullmatch(r"\d{6}", key):
            if not header_found or ended or len(row) != 5:
                raise ValueError(f"Bloque mensual discontinuo o fila inválida: {key}")
            month = pd.Period(f"{key[:4]}-{key[4:]}", freq="M")
            values = [float(v.strip()) for v in row[1:]]
            if any(v in (-99.99, -999) for v in values):
                raise ValueError(f"Factor ausente en {key}")
            rows.append([month, *values]); started = True
        elif started:
            ended = True
    if not rows:
        raise ValueError("No se encontró el bloque mensual AAAAMM")
    frame = pd.DataFrame(rows, columns=["month", *COLUMNS]).set_index("month")
    if frame.index.has_duplicates or not frame.index.is_monotonic_increasing:
        raise ValueError("Meses duplicados o desordenados")
    if not np.isfinite(frame.to_numpy()).all():
        raise ValueError("Factores no finitos")
    return frame / 100.0

def align_factors(returns, factors):
    expected = pd.period_range(returns.index[0], returns.index[-1], freq="M")
    if not returns.index.equals(expected):
        raise ValueError("Meses ausentes, duplicados o desordenados")
    selected = factors.reindex(returns.index)
    if selected.isna().any().any():
        raise ValueError(f"Factores ausentes: {list(selected.index[selected.isna().any(axis=1)].astype(str))}")
    if not np.isfinite(returns.to_numpy()).all():
        raise ValueError("Rentabilidades no finitas")
    return selected
