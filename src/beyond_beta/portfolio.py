import numpy as np
import pandas as pd
from .config import validate_weights

def portfolio_returns(returns, weights):
    weights = validate_weights(weights, returns.shape[1])
    if not np.isfinite(returns.to_numpy()).all():
        raise ValueError("Rentabilidades no finitas")
    return pd.Series(returns.to_numpy() @ weights, index=returns.index, name="Cartera")
