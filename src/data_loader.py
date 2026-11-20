"""Carga, normalización y validación de tablas exportadas desde Tracker."""
from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd


class DataValidationError(ValueError):
    """Los datos experimentales no cumplen las condiciones mínimas del pipeline."""


def _normalize_header(value: object) -> str:
    return re.sub(r"[^a-z0-9]", "", str(value).strip().lower())


def load_tracker_data(path: str | Path) -> tuple[pd.DataFrame, dict[str, int]]:
    """Carga columnas tiempo, x, y desde CSV/TXT exportado por Tracker.

    Reconoce encabezados habituales (t, time, tiempo; x, x-m, x(m); y, y-m,
    y(m)). Devuelve las filas ordenadas por tiempo y un resumen de limpieza.

    Parameters
    ----------
    path : str or pathlib.Path
        Archivo CSV o TXT. Se admite delimitador detectable automáticamente.

    Returns
    -------
    data : pandas.DataFrame
        Columnas normalizadas: t, x, y.
    report : dict
        Filas originales, filas descartadas y filas finales.
    """
    source = Path(path)
    if not source.exists() or not source.is_file():
        raise FileNotFoundError(f"No se encontró el archivo de datos: {source}")
    if source.stat().st_size == 0:
        raise DataValidationError("El archivo está vacío.")

    try:
        raw = pd.read_csv(source, sep=None, engine="python", comment="#", skipinitialspace=True)
    except Exception as exc:
        raise DataValidationError(f"No se pudo interpretar el archivo como tabla CSV/TXT: {exc}") from exc
    if raw.empty or len(raw.columns) < 3:
        raise DataValidationError("Se requieren encabezados y al menos tres columnas (tiempo, x, y).")

    normalized = {_normalize_header(column): column for column in raw.columns}
    aliases = {
        "t": ("t", "time", "tiempo", "times", "timestamp"),
        "x": ("x", "xcoordinate", "posx", "xposition"),
        "y": ("y", "ycoordinate", "posy", "yposition"),
    }
    selected: dict[str, object] = {}
    for target, candidates in aliases.items():
        match = next((normalized[candidate] for candidate in candidates if candidate in normalized), None)
        if match is None:
            # Acepta encabezados con unidades, por ejemplo x_m o y_cm; las unidades
            # deben convertirse a SI antes de ejecutar el análisis.
            match = next((column for key, column in normalized.items()
                          if any(key.startswith(candidate) for candidate in candidates)), None)
        if match is None:
            raise DataValidationError(
                f"No se encontró la columna '{target}'. Encabezados detectados: {list(raw.columns)}"
            )
        selected[target] = match

    data = raw[[selected["t"], selected["x"], selected["y"]]].copy()
    data.columns = ["t", "x", "y"]
    for column in ("t", "x", "y"):
        if data[column].dtype == object:
            # Si el separador de columnas fue detectado y los decimales usan coma,
            # pandas puede dejar los valores como texto.
            data[column] = data[column].astype(str).str.strip().str.replace(",", ".", regex=False)
        data[column] = pd.to_numeric(data[column], errors="coerce")
    original_rows = len(data)
    data = data.replace([np.inf, -np.inf], np.nan).dropna(subset=["t", "x", "y"])
    dropped_rows = original_rows - len(data)
    if len(data) < 5:
        raise DataValidationError(
            f"Se necesitan al menos 5 puntos válidos; solo quedaron {len(data)} (descartados: {dropped_rows})."
        )
    data = data.sort_values("t", kind="stable").reset_index(drop=True)
    time = data["t"].to_numpy(dtype=float)
    if np.any(np.diff(time) <= 0):
        raise DataValidationError("La columna de tiempo debe ser estrictamente creciente y sin duplicados.")
    report = {"original_rows": original_rows, "dropped_rows": dropped_rows, "valid_rows": len(data)}
    return data, report
