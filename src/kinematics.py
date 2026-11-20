"""Suavizado y cálculo numérico de variables cinemáticas."""
from __future__ import annotations

import warnings

import numpy as np
import pandas as pd
from scipy.signal import savgol_filter


def smooth_signal(values: np.ndarray, *, method: str = "savgol", window: int = 9,
                  polyorder: int = 2) -> np.ndarray:
    """Suaviza una señal con Savitzky-Golay, media móvil o sin filtro.

    Savitzky-Golay conserva mejor la forma local y resulta útil antes de derivar.
    Su ventana debe ser impar; se adapta al tamaño de la serie cuando es necesario.
    """
    signal = np.asarray(values, dtype=float)
    if signal.ndim != 1 or signal.size < 3:
        raise ValueError("La señal debe ser un vector con al menos tres observaciones.")
    if not np.all(np.isfinite(signal)):
        raise ValueError("La señal contiene valores no finitos.")
    normalized_method = method.strip().lower()
    if normalized_method in {"none", "ninguno", "raw"}:
        return signal.copy()
    if window < 3:
        raise ValueError("La ventana de suavizado debe ser al menos 3.")
    effective_window = min(int(window), signal.size if signal.size % 2 else signal.size - 1)
    if effective_window % 2 == 0:
        effective_window -= 1
    if effective_window < 3:
        return signal.copy()
    if normalized_method in {"savgol", "savitzky-golay", "savgolay"}:
        effective_polyorder = min(int(polyorder), effective_window - 1)
        if effective_polyorder < 1:
            raise ValueError("El orden polinómico debe ser al menos 1.")
        return savgol_filter(signal, window_length=effective_window,
                             polyorder=effective_polyorder, mode="interp")
    if normalized_method in {"moving", "moving_average", "media_movil"}:
        kernel = np.ones(effective_window, dtype=float) / effective_window
        padded = np.pad(signal, (effective_window // 2,), mode="reflect")
        return np.convolve(padded, kernel, mode="valid")
    raise ValueError("Método desconocido. Usa 'savgol', 'moving' o 'none'.")


def calculate_kinematics(data: pd.DataFrame, *, smoothing: str = "savgol",
                         window: int = 9, polyorder: int = 2,
                         sigma_position: float = 0.001) -> pd.DataFrame:
    """Calcula desplazamiento, velocidad y aceleración mediante `numpy.gradient`.

    Parameters
    ----------
    data : pandas.DataFrame
        Columnas obligatorias `t`, `x`, `y`, con tiempo en segundos y posición en m.
    smoothing : str
        `savgol`, `moving` o `none`.
    window : int
        Número impar aproximado de muestras usadas en el filtro.
    polyorder : int
        Orden del polinomio local de Savitzky-Golay.
    sigma_position : float
        Incertidumbre estándar de una coordenada, en metros. Se usa en la
        aproximación de incertidumbre de diferencias finitas con muestreo uniforme.

    Returns
    -------
    pandas.DataFrame
        Datos originales más coordenadas filtradas, desplazamiento, velocidad,
        rapidez, aceleración y estimaciones de incertidumbre.
    """
    required = {"t", "x", "y"}
    if not required.issubset(data.columns):
        raise ValueError(f"Faltan columnas obligatorias: {sorted(required - set(data.columns))}")
    if sigma_position < 0:
        raise ValueError("sigma_position no puede ser negativa.")
    result = data.copy().reset_index(drop=True)
    t = result["t"].to_numpy(dtype=float)
    if len(t) < 5 or not np.all(np.isfinite(t)) or np.any(np.diff(t) <= 0):
        raise ValueError("Se requieren al menos 5 tiempos finitos, crecientes y sin duplicados.")
    dt = np.diff(t)
    median_dt = float(np.median(dt))
    if np.std(dt) / median_dt > 0.02:
        warnings.warn(
            "El intervalo de muestreo no es uniforme (>2% de variación). "
            "numpy.gradient admite tiempos no uniformes, pero Savitzky-Golay supone muestreo uniforme.",
            RuntimeWarning,
            stacklevel=2,
        )
    result["x_smooth"] = smooth_signal(result["x"].to_numpy(), method=smoothing,
                                        window=window, polyorder=polyorder)
    result["y_smooth"] = smooth_signal(result["y"].to_numpy(), method=smoothing,
                                        window=window, polyorder=polyorder)
    x = result["x_smooth"].to_numpy()
    y = result["y_smooth"].to_numpy()
    result["position_magnitude"] = np.hypot(x, y)
    result["dx"] = x - x[0]
    result["dy"] = y - y[0]
    result["displacement"] = np.hypot(result["dx"], result["dy"])
    result["vx"] = np.gradient(x, t, edge_order=2)
    result["vy"] = np.gradient(y, t, edge_order=2)
    result["speed"] = np.hypot(result["vx"], result["vy"])
    result["ax"] = np.gradient(result["vx"].to_numpy(), t, edge_order=2)
    result["ay"] = np.gradient(result["vy"].to_numpy(), t, edge_order=2)
    result["acceleration_magnitude"] = np.hypot(result["ax"], result["ay"])

    # Aproximación para diferencias centradas y errores de posición independientes.
    # sigma_v = sqrt(2)*sigma_x/(2*dt); sigma_a = sqrt(6)*sigma_x/dt².
    result["sigma_position"] = float(sigma_position)
    result["sigma_velocity"] = np.sqrt(2.0) * sigma_position / (2.0 * median_dt)
    result["sigma_acceleration"] = np.sqrt(6.0) * sigma_position / (median_dt ** 2)
    return result
