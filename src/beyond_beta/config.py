"""Configuración validada; la raíz no depende de la ubicación del TOML."""
from copy import deepcopy
from pathlib import Path
import re
import tomllib
import numpy as np
import pandas as pd

HAC_RULE = "floor(4*(T/100)^(2/9))"


def project_root(start=None):
    start = Path(start or Path.cwd()).resolve()
    for candidate in [start, *start.parents]:
        marker = candidate / "pyproject.toml"
        if marker.is_file():
            with marker.open("rb") as handle:
                if tomllib.load(handle).get("project", {}).get("name") == "beyond-beta":
                    return candidate
    raise ValueError("No se encuentra la raíz beyond-beta; usa --project-root o ejecuta desde el proyecto")


def validate_weights(weights, count):
    values = np.asarray(weights, dtype=float)
    if values.ndim != 1 or len(values) != count or not np.isfinite(values).all():
        raise ValueError("Los pesos deben ser una lista finita alineada con los activos")
    if (values <= 0).any() or not np.isclose(values.sum(), 1, atol=1e-10, rtol=0):
        raise ValueError("Diseño sin cortos: pesos estrictamente positivos cuya suma sea 1 (tolerancia 1e-10)")
    return values


def hac_lags(observations):
    return int(np.floor(4 * (observations / 100) ** (2 / 9)))


def load_config(path="config/analysis.toml", root=None):
    root = Path(root).resolve() if root is not None else project_root()
    path = Path(path)
    path = path.resolve() if path.is_absolute() else (root / path).resolve()
    with path.open("rb") as handle:
        config = tomllib.load(handle)
    allowed = {
        "sample": {"price_start", "price_end", "expected_prices", "expected_returns", "currency", "max_fx_age_days", "max_month_end_age_days"},
        "assets": {"tickers", "names", "currencies", "weights"},
        "factors": {"file", "source", "sha256", "url"},
        "inference": {"primary", "hac_rule"},
        "portfolio": {"rebalance", "costs", "taxes"},
    }
    if set(config) != set(allowed):
        raise ValueError("Secciones de configuración ausentes o no admitidas")
    for section, keys in allowed.items():
        if set(config[section]) != keys:
            raise ValueError(f"Campos ausentes o no admitidos en {section}: {set(config[section]) ^ keys}")
    assets, sample = config["assets"], config["sample"]
    lists = [assets[key] for key in ["tickers", "names", "currencies", "weights"]]
    if not all(isinstance(value, list) for value in lists) or len({len(value) for value in lists}) != 1 or not 2 <= len(lists[0]) <= 10:
        raise ValueError("Se admiten de dos a diez activos y listas de igual longitud")
    for key in ["tickers", "names"]:
        values = assets[key]
        if not all(isinstance(value, str) and value.strip() == value and value for value in values):
            raise ValueError(f"{key}: identificadores vacíos o con espacios exteriores")
        if len({value.casefold() for value in values}) != len(values):
            raise ValueError(f"{key}: identificadores duplicados")
    if "cartera" in {name.casefold() for name in assets["names"]}:
        raise ValueError("Cartera es un nombre reservado")
    if "EURUSD=X" in assets["tickers"] or not all(re.fullmatch(r"[A-Za-z0-9.^-]+", ticker) for ticker in assets["tickers"]):
        raise ValueError("Ticker reservado o no admitido como nombre de snapshot")
    if not set(assets["currencies"]) <= {"EUR", "USD"}:
        raise ValueError("Divisas admitidas para activos: EUR y USD")
    validate_weights(assets["weights"], len(assets["tickers"]))
    if sample["currency"] != "USD":
        raise ValueError("Los factores configurados solo permiten regresiones en USD")
    if not all(isinstance(sample[key], str) and re.fullmatch(r"\d{4}-\d{2}", sample[key]) for key in ["price_start", "price_end"]):
        raise ValueError("Los límites de muestra deben ser AAAA-MM")
    periods = pd.period_range(sample["price_start"], sample["price_end"], freq="M")
    for key in ["expected_prices", "expected_returns", "max_fx_age_days", "max_month_end_age_days"]:
        if type(sample[key]) is not int:
            raise ValueError(f"sample.{key} debe ser entero")
    if len(periods) < 13 or len(periods) != sample["expected_prices"] or len(periods) - 1 != sample["expected_returns"]:
        raise ValueError("Se exigen al menos 12 rentabilidades y recuentos coherentes con la ventana")
    if not 0 <= sample["max_fx_age_days"] <= 10 or not 0 <= sample["max_month_end_age_days"] <= 10:
        raise ValueError("Las tolerancias de frescura deben estar entre 0 y 10 días naturales")
    if config["inference"] != {"primary": "OLS", "hac_rule": HAC_RULE}:
        raise ValueError(f"Inferencia admitida: primary=OLS y hac_rule={HAC_RULE}; HAC es sensibilidad")
    portfolio = config["portfolio"]
    if portfolio["rebalance"] != "monthly" or portfolio["costs"] != 0 or portfolio["taxes"] != 0:
        raise ValueError("Solo se admite rebalanceo monthly, costs=0 y taxes=0; no se simulan costes ni fiscalidad")
    if not re.fullmatch(r"[a-fA-F0-9]{64}", config["factors"]["sha256"]):
        raise ValueError("SHA256 de factores no válido")
    factor_path = Path(config["factors"]["file"])
    if factor_path.is_absolute() or ".." in factor_path.parts:
        raise ValueError("factors.file debe ser una ruta relativa dentro del proyecto")
    if not all(isinstance(config['factors'][key],str) and config['factors'][key].strip() for key in ['file','source','url']):
        raise ValueError('La ruta, atribución y URL de factores deben ser textos no vacíos')
    config["parameters"] = deepcopy(config)
    config["root"], config["config_path"] = root, path
    return config
