import numpy as np
import pandas as pd

def monthly_observations(daily, periods, max_end_age=7, ticker="serie"):
    if not isinstance(daily.index, pd.DatetimeIndex) or daily.index.hasnans:
        raise ValueError(f"{ticker}: fechas diarias no válidas")
    if daily.index.has_duplicates:
        raise ValueError(f"{ticker}: fechas diarias duplicadas")
    daily = daily.dropna().sort_index()
    key = daily.index.to_period("M")
    prices = daily.groupby(key).last().reindex(periods)
    dates = pd.Series(daily.index, index=daily.index).groupby(key).last().reindex(periods)
    if prices.isna().any() or dates.isna().any() or (prices <= 0).any():
        bad = prices.index[prices.isna() | (prices <= 0)]
        raise ValueError(f"{ticker}: precio mensual ausente o no positivo en {list(bad.astype(str))}")
    if not np.isfinite(prices.to_numpy()).all():
        raise ValueError(f"{ticker}: precios mensuales no finitos")
    for month, date in dates.items():
        age = (month.end_time.normalize() - date.normalize()).days
        if age < 0 or age > max_end_age:
            raise ValueError(f"{ticker}: mes {month}, observación {date.date()}, distancia al fin de mes {age} días; máximo {max_end_age}")
    return prices, dates

def fx_at_dates(fx, dates, max_age=4):
    fx = fx.dropna().sort_index()
    if fx.index.has_duplicates:
        raise ValueError("Fechas FX duplicadas")
    positions = fx.index.get_indexer(pd.DatetimeIndex(dates), method="pad")
    if (positions < 0).any():
        raise ValueError("No hay cambio anterior o coincidente")
    selected_dates = pd.Series(fx.index[positions], index=dates.index)
    ages = (dates - selected_dates).dt.days
    if (ages < 0).any() or (ages > max_age).any():
        raise ValueError("Cambio futuro o demasiado antiguo")
    rates = pd.Series(fx.iloc[positions].to_numpy(), index=dates.index)
    if not np.isfinite(rates).all() or (rates <= 0).any():
        raise ValueError("Cambio no válido")
    return rates, selected_dates, ages

def convert_prices(prices, fx, currency, target):
    if currency == target:
        return prices.copy()
    if currency == "EUR" and target == "USD":
        return prices * fx
    if currency == "USD" and target == "EUR":
        return prices / fx
    raise ValueError(f"Conversión no soportada: {currency}/{target}")

def simple_returns(prices):
    if len(prices) < 2:
        raise ValueError("Se requieren al menos dos precios")
    if prices.isna().any().any() or not np.isfinite(prices.to_numpy()).all() or (prices <= 0).any().any():
        raise ValueError("Precios ausentes, no finitos o no positivos")
    expected = pd.period_range(prices.index[0], prices.index[-1], freq="M")
    if not prices.index.equals(expected):
        raise ValueError("Meses ausentes, duplicados o desordenados")
    return prices.pct_change(fill_method=None).iloc[1:]

def prepare_prices(config):
    root, assets, sample = config["root"], config["assets"], config["sample"]
    periods = pd.period_range(sample["price_start"], sample["price_end"], freq="M")
    fx = pd.read_csv(root / "data/raw/EURUSD_X.csv", index_col=0, parse_dates=True)["Close"]
    original, usd, eur, observations = {}, {}, {}, []
    for ticker, currency, name in zip(assets["tickers"], assets["currencies"], assets["names"]):
        frame = pd.read_csv(root / f"data/raw/{ticker}.csv", index_col=0, parse_dates=True)
        prices, dates = monthly_observations(frame["Adj Close"], periods, sample["max_month_end_age_days"], ticker)
        try:
            rates, fx_dates, ages = fx_at_dates(fx, dates, sample["max_fx_age_days"])
        except ValueError as exc:
            raise ValueError(f"{ticker}: {exc}") from exc
        original[name] = prices
        usd[name] = convert_prices(prices, rates, currency, "USD")
        eur[name] = convert_prices(prices, rates, currency, "EUR")
        observations.extend({"month": str(m), "ticker": ticker, "currency": currency,
          "price_date": str(dates.loc[m].date()), "fx_date": str(fx_dates.loc[m].date()),
          "fx_age_days": int(ages.loc[m]), "USD_per_EUR": float(rates.loc[m])} for m in periods)
    frames = {"prices_original": pd.DataFrame(original), "prices_usd": pd.DataFrame(usd), "prices_eur": pd.DataFrame(eur)}
    frames["returns_usd"] = simple_returns(frames["prices_usd"])
    frames["returns_eur"] = simple_returns(frames["prices_eur"])
    frames["observations"] = pd.DataFrame(observations)
    return frames
