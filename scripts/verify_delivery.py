"""Recalculate the submitted monthly results offline, without changing any file.

Uses numeric original prices, FX and factors in the delivered workbook; it does
not evaluate Excel formulas or claim to authenticate the missing daily snapshots.
"""
import argparse
import json
from pathlib import Path
import tomllib

import numpy as np
import pandas as pd
from openpyxl import load_workbook
from scipy.stats import t as student_t


def verify(root):
    root = Path(root).resolve()
    config = tomllib.loads((root / 'config/analysis.toml').read_text(encoding='utf-8'))
    workbook = load_workbook(root / 'reports/Resultados_Beyond_Beta.xlsx', data_only=False, read_only=True)
    checks = 0
    maximum_error = 0.0

    def check(label, actual, expected):
        nonlocal checks, maximum_error
        a, b = np.asarray(actual, dtype=float), np.asarray(expected, dtype=float)
        if a.shape != b.shape or not np.isfinite(a).all() or not np.isfinite(b).all():
            raise ValueError(f'{label}: dimensiones o números no válidos')
        error = float(np.max(np.abs(a - b)))
        if not np.allclose(a, b, rtol=1e-10, atol=1e-10):
            raise ValueError(f'{label}: diferencia máxima {error}')
        checks += 1
        maximum_error = max(maximum_error, error)

    def sheet(name):
        rows = iter(workbook[name].values)
        return pd.DataFrame(rows, columns=next(rows))

    def dated(name):
        frame = sheet(name).set_index('Mes')
        frame.index = pd.DatetimeIndex(frame.index).to_period('M')
        if frame.index.has_duplicates or not frame.index.is_monotonic_increasing:
            raise ValueError(f'{name}: meses duplicados o desordenados')
        return frame

    def table(name, index=False):
        return pd.read_csv(root / f'reports/tables/{name}.csv', index_col=0 if index else None)

    try:
        names = config['assets']['names']
        tickers = config['assets']['tickers']
        currencies = config['assets']['currencies']
        weights = np.array(config['assets']['weights'])
        original = dated('Precios_originales')
        expected_months = pd.period_range(config['sample']['price_start'], config['sample']['price_end'], freq='M')
        if list(original.columns) != names or not original.index.equals(expected_months):
            raise ValueError('Precios_originales: universo o ventana diferente de configuración')
        if len(original) != config['sample']['expected_prices']:
            raise ValueError('Número de precios incompatible con configuración')
        if not np.isfinite(original.to_numpy(dtype=float)).all() or (original <= 0).any().any():
            raise ValueError('Precios originales no positivos o no finitos')
        weight_sheet = sheet('Pesos')
        if list(weight_sheet['Activo']) != names or list(weight_sheet['Ticker']) != tickers or list(weight_sheet['Divisa original']) != currencies:
            raise ValueError('Pesos: identidad de activos diferente de configuración')
        check('pesos del Excel', weight_sheet['Peso'], weights)
        if (weights <= 0).any() or not np.isclose(weights.sum(), 1, rtol=0, atol=1e-10):
            raise ValueError('Pesos no válidos')
        observations = sheet('Fechas_y_FX').set_index(['ticker', 'Mes'])
        if observations.index.has_duplicates or len(observations) != len(original) * len(names):
            raise ValueError('Observaciones FX duplicadas o incompletas')
        prices = {'usd': original.copy(), 'eur': original.copy()}
        for name, ticker, currency in zip(names, tickers, currencies):
            rows = observations.loc[[(ticker, str(month)) for month in original.index]]
            if not rows['Divisa'].eq(currency).all():
                raise ValueError(f'{ticker}: divisa incoherente')
            fx = rows['USD por EUR'].to_numpy(dtype=float)
            if not np.isfinite(fx).all() or (fx <= 0).any():
                raise ValueError(f'{ticker}: cambio no válido')
            price_dates, fx_dates = pd.to_datetime(rows['Fecha precio']), pd.to_datetime(rows['Fecha FX'])
            age = (price_dates - fx_dates).dt.days.to_numpy()
            check(f'{ticker}: antigüedad FX', rows['Antigüedad FX días'], age)
            if (age < 0).any() or (age > config['sample']['max_fx_age_days']).any():
                raise ValueError(f'{ticker}: FX posterior o demasiado antiguo')
            if list(price_dates.dt.to_period('M')) != list(original.index):
                raise ValueError(f'{ticker}: fechas de precios fuera de mes')
            month_end_age = (original.index.to_timestamp(how='end').normalize() - pd.DatetimeIndex(price_dates)).days
            if (month_end_age < 0).any() or (month_end_age > config['sample']['max_month_end_age_days']).any():
                raise ValueError(f'{ticker}: cierre mensual demasiado antiguo')
            if currency == 'EUR':
                prices['usd'][name] = original[name].to_numpy() * fx
            elif currency == 'USD':
                prices['eur'][name] = original[name].to_numpy() / fx
            else:
                raise ValueError(f'{ticker}: divisa no soportada')
        combined = {}
        for target, frame in prices.items():
            returns = frame.to_numpy()[1:] / frame.to_numpy()[:-1] - 1
            combined[target] = pd.DataFrame(returns, index=original.index[1:], columns=names)
            combined[target]['Cartera'] = returns @ weights
            saved = table(f'returns_{target}', index=True)
            if list(saved.columns) != names + ['Cartera'] or list(saved.index) != list(original.index[1:].astype(str)):
                raise ValueError(f'returns_{target}: columnas o meses distintos')
            check(f'retornos {target}', saved, combined[target])
            wealth = np.cumprod(1 + combined[target].to_numpy(), axis=0)
            peaks = np.maximum.accumulate(np.vstack([np.ones(wealth.shape[1]), wealth]), axis=0)[1:]
            vol = combined[target].to_numpy().std(axis=0, ddof=1)
            metrics = {
                'cumulative_return': wealth[-1] - 1,
                'geometric_annual_return': wealth[-1] ** (12 / len(wealth)) - 1,
                'mean_monthly': combined[target].to_numpy().mean(axis=0),
                'vol_monthly': vol, 'vol_annual': vol * np.sqrt(12),
                'max_drawdown_monthly': (wealth / peaks - 1).min(axis=0),
            }
            summary = table(f'descriptive_{target}', index=True)
            if list(summary.index) != names + ['Cartera'] or set(summary.columns) != set(metrics):
                raise ValueError(f'descriptive_{target}: etiquetas incompatibles')
            for field, values in metrics.items():
                check(f'{target}: {field}', summary[field], values)
        correlations = table('correlations', index=True)
        if list(correlations.index) != names + ['Cartera'] or list(correlations.columns) != names + ['Cartera']:
            raise ValueError('Correlaciones: etiquetas incompatibles')
        check('correlaciones', correlations, np.corrcoef(combined['usd'].to_numpy(), rowvar=False))
        factors = dated('Factores_USD')
        if not factors.index.equals(original.index[1:]) or list(factors.columns) != ['Mkt-RF', 'SMB', 'HML', 'RF']:
            raise ValueError('Factores: meses o columnas diferentes de retornos')
        if len(factors) != config['sample']['expected_returns']:
            raise ValueError('Número de retornos incompatible con configuración')
        capm, ff3 = table('capm'), table('ff3')
        if len(capm) != 4 * (len(names) + 1) or len(ff3) != 8:
            raise ValueError('Inventario de regresiones incompleto o inesperado')
        if set(capm.asset) != set(names + ['Cartera']) or not ff3.asset.eq('Cartera').all():
            raise ValueError('Identidad de activos incompatible en las regresiones')
        comparisons = []
        jobs = [(name, ['Mkt-RF'], capm[capm.asset == name]) for name in names + ['Cartera']]
        jobs.append(('Cartera', ['Mkt-RF', 'SMB', 'HML'], ff3))
        for asset, columns, saved in jobs:
            x = np.column_stack([np.ones(len(factors)), factors[columns].to_numpy()])
            y = (combined['usd'][asset] - factors.RF).to_numpy()
            if not np.isfinite(x).all() or not np.isfinite(y).all() or np.linalg.matrix_rank(x) != x.shape[1]:
                raise ValueError(f'{asset}: diseño no válido')
            n, k = x.shape
            coef = np.linalg.lstsq(x, y, rcond=None)[0]
            residual = y - x @ coef
            rss = residual @ residual
            bread = np.linalg.inv(x.T @ x)
            lags = int(np.floor(4 * (n / 100) ** (2 / 9)))
            scores = x * residual[:, None]
            meat = scores.T @ scores
            for lag in range(1, lags + 1):
                cross = scores[lag:].T @ scores[:-lag]
                meat += (1 - lag / (lags + 1)) * (cross + cross.T)
            covariances = {'OLS': rss / (n - k) * bread, 'HAC': bread @ meat @ bread * n / (n - k)}
            r2 = 1 - rss / np.sum((y - y.mean()) ** 2)
            adjusted = 1 - (1 - r2) * (n - 1) / (n - k)
            for inference, covariance in covariances.items():
                rows = saved[saved.inference == inference].set_index('term')
                terms = ['alpha'] + columns
                if len(rows) != k or rows.index.has_duplicates or set(rows.index) != set(terms):
                    raise ValueError(f'{asset}/{inference}: términos incompatibles')
                rows = rows.loc[terms]
                se = np.sqrt(np.diag(covariance))
                t_stat = coef / se
                critical = student_t.ppf(.975, n - k)
                expected = {
                    'coefficient': coef, 'std_error': se, 't_stat': t_stat,
                    'p_value': 2 * student_t.sf(np.abs(t_stat), n - k),
                    'ci_low': coef - critical * se, 'ci_high': coef + critical * se,
                    'r_squared': np.full(k, r2), 'adj_r_squared': np.full(k, adjusted),
                    'n_obs': np.full(k, n), 'hac_lags': np.full(k, lags if inference == 'HAC' else 0),
                }
                for field, values in expected.items():
                    check(f'{asset}/{len(columns)}/{inference}/{field}', rows[field], values)
            if asset == 'Cartera':
                ll = -n / 2 * (np.log(2 * np.pi) + np.log(rss / n) + 1)
                comparisons.append([n, r2, adjusted, -2 * ll + 2 * k, -2 * ll + k * np.log(n)])
        comparison = table('comparison').set_index('model')
        if set(comparison.index) != {'CAPM', 'FF3'} or len(comparison) != 2:
            raise ValueError('Comparación de modelos incompleta')
        check('comparación de modelos', comparison.loc[['CAPM', 'FF3'], ['n_obs', 'r_squared', 'adj_r_squared', 'aic', 'bic']], comparisons)
        return {'checks': checks, 'regressions': len(jobs), 'months': len(factors),
                'max_absolute_difference': maximum_error,
                'scope': 'Monthly values in delivered Excel versus CSV results; daily source provenance is not certified.'}
    finally:
        workbook.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project-root', type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    print(json.dumps(verify(args.project_root), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
