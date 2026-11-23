"""Integridad de etapas y artefactos, sin hashes autorreferenciales."""
from datetime import datetime, timezone
from hashlib import sha256
import importlib.metadata
import json
from pathlib import Path
import platform
import subprocess
from uuid import uuid4
from .download import file_hash

TABLE_FILES = [f"reports/tables/{name}.csv" for name in [
    "descriptive_usd", "descriptive_eur", "capm", "ff3", "comparison", "correlations", "returns_usd", "returns_eur"]]
FIGURE_FILES = [f"reports/figures/{name}.png" for name in [
    "wealth_usd", "correlations_usd", "risk_return_usd", "sml_usd", "capm_scatter_usd"]]
WORKBOOK = "reports/Resultados_Beyond_Beta.xlsx"


def write_json(path, value):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")
    temporary.replace(path)


def source_hashes(config):
    root = config["root"]
    manifest_path = root / "data/raw/manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    paths = [manifest_path]
    for ticker, currency in zip(config["assets"]["tickers"] + ["EURUSD=X"], config["assets"]["currencies"] + ["USD"]):
        path = root / f"data/raw/{ticker.replace('=', '_')}.csv"
        entry = manifest.get(ticker, {})
        field = "Close" if ticker == "EURUSD=X" else "Adj Close"
        if entry.get("sha256") != file_hash(path) or entry.get("currency") != currency or entry.get("field") != field:
            raise ValueError(f"Snapshot o procedencia incompatibles: {ticker}")
        paths.append(path)
    factor_path = root / config["factors"]["file"]
    if file_hash(factor_path).lower() != config["factors"]["sha256"].lower():
        raise ValueError("Los factores no coinciden con el SHA256 configurado")
    paths.append(factor_path)
    return {path.relative_to(root).as_posix(): file_hash(path) for path in paths}


def code_state(root):
    paths = sorted(path for path in (root / "src/beyond_beta").glob("*.py") if path.name not in {"report.py", "latex.py"})
    digest = sha256()
    for path in paths:
        digest.update(path.name.encode()); digest.update(path.read_bytes())
    def git(*args):
        try:
            result = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, timeout=10)
            return result.stdout.strip() if result.returncode == 0 else None
        except (OSError, subprocess.TimeoutExpired):
            return None
    return {"commit": git("rev-parse", "HEAD"), "dirty": bool(git("status", "--porcelain")), "analysis_source_sha256": digest.hexdigest()}


def artifact_hashes(root, paths):
    return {Path(path).as_posix(): file_hash(root / path) for path in paths}


def begin_analysis(config, validation):
    root = config["root"]
    run = {"schema_version": 2, "stage": "building", "run_id": uuid4().hex,
           "executed_at": datetime.now(timezone.utc).isoformat(), "python": platform.python_version(),
           "versions": {name: importlib.metadata.version(name) for name in ["pandas", "numpy", "statsmodels", "scipy", "matplotlib", "yfinance", "openpyxl"]},
           "config_path": str(config["config_path"]), "config_sha256": file_hash(config["config_path"]),
           "parameters": config["parameters"], "validation": validation, "inputs": source_hashes(config), "code": code_state(root)}
    write_json(root / "reports/run_manifest.json", run)
    return run


def finish_analysis(config, run):
    run["analysis_outputs"] = artifact_hashes(config["root"], TABLE_FILES + FIGURE_FILES + [WORKBOOK])
    run["excel_validation"] = {"cached_results": False, "status": "openpyxl no calcula fórmulas; recálculo solicitado al abrir"}
    run["stage"] = "analysis_complete"
    write_json(config["root"] / "reports/run_manifest.json", run)


def validate_analysis(config, skip_workbook=False):
    root = config["root"]
    run = json.loads((root / "reports/run_manifest.json").read_text(encoding="utf-8"))
    if run.get("schema_version") != 2 or run.get("stage") not in {"analysis_complete", "report_building", "report_complete"}:
        raise ValueError("No hay una ejecución completa válida; ejecuta analyze")
    if Path(run['config_path']).resolve()!=config['config_path'] or run["config_sha256"] != file_hash(config["config_path"]) or run["parameters"] != config["parameters"]:
        raise ValueError("La configuración efectiva difiere de la utilizada en analyze")
    if run["inputs"] != source_hashes(config):
        raise ValueError("Las entradas o su procedencia cambiaron desde analyze; no se atribuyen a resultados antiguos")
    if run["code"]["analysis_source_sha256"] != code_state(root)["analysis_source_sha256"]:
        raise ValueError("El código de análisis cambió; repite analyze")
    expected = set(TABLE_FILES + FIGURE_FILES + [WORKBOOK])
    if set(run["analysis_outputs"]) != expected:
        raise ValueError("Inventario de artefactos de análisis incompleto o inesperado")
    for name, digest in run["analysis_outputs"].items():
        if skip_workbook and name == WORKBOOK:
            continue
        if not (root / name).is_file() or file_hash(root / name) != digest:
            raise ValueError(f"Artefacto alterado o de otra ejecución: {name}")
    if "numeric_validation" in run:
        evidence=run['numeric_validation']
        if file_hash(root/evidence['path'])!=evidence['sha256']:
            raise ValueError('Verificación numérica alterada')
    return run


def record_report(config, run, inputs, outputs):
    run["report_inputs"] = artifact_hashes(config["root"], inputs)
    run["report_outputs"] = artifact_hashes(config["root"], outputs)
    run["stage"] = "report_complete"
    write_json(config["root"] / "reports/run_manifest.json", run)


def validate_report(config):
    run = validate_analysis(config)
    if run["stage"] != "report_complete":
        raise ValueError("Informe no completado")
    for group in ["report_inputs", "report_outputs"]:
        for name, digest in run[group].items():
            if file_hash(config["root"] / name) != digest:
                raise ValueError(f"Documento o fuente alterados: {name}")
    return run


def record_excel_validation(config, original_sha256, evidence):
    """Registro explícito tras verificar con un motor externo y guardar el libro."""
    run = validate_analysis(config, skip_workbook=True)
    if run["analysis_outputs"][WORKBOOK] != original_sha256:
        raise ValueError("El libro de partida no pertenece a esta ejecución")
    current = file_hash(config["root"] / WORKBOOK)
    if evidence["workbook_sha256"] != current or not evidence["cached_results"]:
        raise ValueError("Evidencia de recálculo incompatible con el libro")
    run["analysis_outputs"][WORKBOOK] = current
    run["excel_validation"] = evidence
    run["stage"] = "analysis_complete"
    run.pop("report_inputs", None); run.pop("report_outputs", None)
    write_json(config["root"] / "reports/run_manifest.json", run)
