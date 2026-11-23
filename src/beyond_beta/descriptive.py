import numpy as np
import pandas as pd

def descriptive_statistics(returns):
    if not np.isfinite(returns.to_numpy()).all() or (returns <= -1).any().any():
        raise ValueError("Rentabilidades ausentes o incompatibles con la capitalización")
    wealth = (1 + returns).cumprod()
    # Include initial wealth 1 in the high-water mark.
    peaks = wealth.cummax().clip(lower=1)
    return pd.DataFrame({"cumulative_return": wealth.iloc[-1]-1,
        "geometric_annual_return": wealth.iloc[-1] ** (12/len(returns))-1,
        "mean_monthly": returns.mean(), "vol_monthly": returns.std(ddof=1),
        "vol_annual": returns.std(ddof=1)*np.sqrt(12),
        "max_drawdown_monthly": (wealth/peaks-1).min()})
