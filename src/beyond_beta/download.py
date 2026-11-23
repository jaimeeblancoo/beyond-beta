"""Descargas explícitas; el análisis posterior no realiza peticiones de red."""
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import shutil
import io
import urllib.request
import zipfile
import pandas as pd
from .preparation import monthly_observations

def file_hash(path):
    return sha256(Path(path).read_bytes()).hexdigest()

def download_prices(config, refresh=False):
    import yfinance as yf
    root = config["root"]
    raw = root / "data/raw"
    raw.mkdir(parents=True, exist_ok=True)
    manifest_path = raw / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
    start = pd.Period(config["sample"]["price_start"], "M").start_time - pd.Timedelta(days=7)
    end = (pd.Period(config["sample"]["price_end"], "M") + 1).start_time
    for ticker, currency in zip(config["assets"]["tickers"] + ["EURUSD=X"], config["assets"]["currencies"] + ["USD"]):
        path = raw / f"{ticker.replace('=', '_')}.csv"
        field = "Close" if ticker == "EURUSD=X" else "Adj Close"
        periods = pd.period_range(config["sample"]["price_start"], config["sample"]["price_end"], freq="M")
        if path.exists() and not refresh:
            local = pd.read_csv(path, index_col=0, parse_dates=True)
            monthly_observations(local[field], periods, config['sample']['max_month_end_age_days'], ticker)
            if manifest.get(ticker, {}).get("sha256") != file_hash(path):
                raise ValueError(f"Fuente local alterada o sin manifest: {ticker}")
            print(f"Copia local válida: {ticker}", flush=True)
            continue
        try:
            obj = yf.Ticker(ticker)
            frame = obj.history(start=str(start.date()), end=str(end.date()), interval="1d", auto_adjust=False, actions=True, timeout=20)
            if frame.empty or field not in frame:
                raise ValueError("La fuente devolvió una serie vacía o sin el campo solicitado")
            frame.index = frame.index.tz_localize(None)
            frame.index.name = "Date"
            monthly_observations(frame[field], periods, config['sample']['max_month_end_age_days'], ticker)
            metadata = obj.history_metadata
            if metadata.get("currency") != currency:
                raise ValueError(f"Divisa inesperada: {metadata.get('currency')}; esperada {currency}")
            if path.exists():
                archive = raw / "archive" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
                archive.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, archive / path.name)
            frame.to_csv(path)
            manifest[ticker] = {"ticker": ticker, "currency": currency, "field": field,
                "name": metadata.get("longName", metadata.get("shortName")),
                "downloaded_at": datetime.now(timezone.utc).isoformat(), "provider": "Yahoo Finance via yfinance",
                "url": f"https://finance.yahoo.com/quote/{ticker}/history/", "sha256": file_hash(path),
                "daily_start": str(frame.index[0].date()), "daily_end": str(frame.index[-1].date())}
            manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
            print(f"Validado {ticker}: {len(periods)} meses, {currency}, {manifest[ticker]['name']}", flush=True)
        except Exception as exc:
            if path.exists():
                local = pd.read_csv(path, index_col=0, parse_dates=True)
                monthly_observations(local[field], periods, config['sample']['max_month_end_age_days'], ticker)
                if manifest.get(ticker, {}).get("sha256") == file_hash(path):
                    print(f"ERROR descarga {ticker}: {exc}. Se mantiene la copia local válida.", flush=True)
                    continue
            raise RuntimeError(f"Descarga fallida para {ticker}: {exc}") from exc
    return manifest

def download_official_factors(config):
    """Acción alternativa explícita; nunca se ejecuta al analizar datos locales."""
    target = config["root"] / "data/raw/kenneth_french_official.csv"
    if target.exists():
        raise FileExistsError("La descarga oficial ya existe; no se sobrescribe")
    request = urllib.request.Request(config["factors"]["url"], headers={"User-Agent": "beyond-beta academic project"})
    with urllib.request.urlopen(request, timeout=40) as response:
        content = response.read()
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        member = next(name for name in archive.namelist() if name.lower().endswith('.csv'))
        data = archive.read(member)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    target.with_suffix('.provenance.json').write_text(json.dumps({"url":config["factors"]["url"],
        "downloaded_at":datetime.now(timezone.utc).isoformat(), "sha256":file_hash(target),
        "source":"Biblioteca oficial Kenneth French; no identificada como copia del profesor"}, indent=2), encoding='utf-8')
    return target
