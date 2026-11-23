import numpy as np
import pandas as pd
from statsmodels.regression.linear_model import OLS
from statsmodels.tools.tools import add_constant
from .config import hac_lags

def fit_model(returns, factors, columns):
    if len(returns) <= len(columns) + 1:
        raise ValueError("Observaciones insuficientes: los grados de libertad residuales deben ser positivos")
    if not returns.index.equals(factors.index):
        raise ValueError("Muestras distintas")
    if returns.index.has_duplicates or not returns.index.is_monotonic_increasing:
        raise ValueError('Fechas duplicadas o desordenadas en regresión')
    y = returns - factors["RF"]
    x = add_constant(factors[columns], has_constant="add")
    if not np.isfinite(x.to_numpy()).all() or not np.isfinite(y).all():
        raise ValueError("NaN o infinitos en regresión")
    if np.linalg.matrix_rank(x) != x.shape[1]:
        raise ValueError("Diseño de regresión singular")
    fit = OLS(y, x, missing="raise").fit()
    lags = hac_lags(len(y))
    hac = fit.get_robustcov_results(cov_type="HAC", maxlags=lags, use_correction=True, use_t=True)
    records = []
    for inference, result in [("OLS",fit),("HAC",hac)]:
        intervals = np.asarray(result.conf_int(alpha=.05))
        for i, term in enumerate(x.columns):
            records.append({"term": "alpha" if term == "const" else term, "inference": inference,
                "coefficient": float(np.asarray(result.params)[i]), "std_error": float(np.asarray(result.bse)[i]),
                "t_stat": float(np.asarray(result.tvalues)[i]), "p_value": float(np.asarray(result.pvalues)[i]),
                "ci_low": float(intervals[i,0]), "ci_high": float(intervals[i,1]),
                "r_squared":float(fit.rsquared), "adj_r_squared":float(fit.rsquared_adj),
                "n_obs":int(fit.nobs), "hac_lags":lags if inference=="HAC" else 0})
    return pd.DataFrame(records), fit

def capm(returns, factors):
    return fit_model(returns, factors, ["Mkt-RF"])
