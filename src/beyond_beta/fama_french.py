from .capm import fit_model

def fama_french(returns, factors):
    return fit_model(returns, factors, ["Mkt-RF", "SMB", "HML"])
