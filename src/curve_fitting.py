"""Ajustes de modelos y métricas estadísticas para datos cinemáticos."""
from __future__ import annotations

from typing import Any

import numpy as np
from scipy.optimize import curve_fit


def linear_model(t: np.ndarray, intercept: float, slope: float) -> np.ndarray:
    return intercept + slope * t


def free_fall_model(t: np.ndarray, y0: float, v0: float, acceleration: float) -> np.ndarray:
    """Modelo y(t)=y0+v0*t+(1/2)*a*t²; el signo depende de los ejes elegidos."""
    return y0 + v0 * t + 0.5 * acceleration * t ** 2


def _metrics(observed: np.ndarray, predicted: np.ndarray) -> dict[str, float]:
    residuals = observed - predicted
    ss_res = float(np.sum(residuals ** 2))
    ss_tot = float(np.sum((observed - np.mean(observed)) ** 2))
    r_squared = 1.0 - ss_res / ss_tot if ss_tot > 0 else float("nan")
    return {
        "r_squared": r_squared,
        "rmse": float(np.sqrt(np.mean(residuals ** 2))),
        "mae": float(np.mean(np.abs(residuals))),
        "residual_std": float(np.std(residuals, ddof=1)) if len(residuals) > 1 else 0.0,
    }



def detect_quadratic_outliers(t: np.ndarray, y: np.ndarray, *, threshold: float = 4.5) -> dict[str, Any]:
    """Marca posibles valores atípicos mediante residuos y desviación MAD robusta.

    La función no elimina puntos: devuelve una máscara para inspección y
    documentación. La decisión de excluir una observación debe justificarse
    con evidencia experimental o un error de seguimiento identificable.
    """
    t = np.asarray(t, dtype=float)
    y = np.asarray(y, dtype=float)
    if len(t) != len(y) or len(t) < 5 or threshold <= 0:
        raise ValueError("Se requieren al menos 5 pares t/y y un umbral positivo.")
    coefficients = np.polyfit(t, y, 2)
    residuals = y - np.polyval(coefficients, t)
    median_residual = float(np.median(residuals))
    mad = float(np.median(np.abs(residuals - median_residual)))
    robust_sigma = 1.4826 * mad
    if robust_sigma <= np.finfo(float).eps:
        robust_sigma = float(np.std(residuals, ddof=1))
    if robust_sigma <= np.finfo(float).eps:
        mask = np.zeros(len(y), dtype=bool)
    else:
        mask = np.abs(residuals - median_residual) > threshold * robust_sigma
    return {"mask": mask, "residuals": residuals, "robust_sigma": robust_sigma,
            "threshold": float(threshold), "count": int(np.count_nonzero(mask))}


def fit_free_fall(t: np.ndarray, y: np.ndarray, *, sigma_y: float | np.ndarray | None = None,
                  gravity_reference: float = 9.81) -> dict[str, Any]:
    """Ajusta la trayectoria vertical a un modelo de aceleración constante.

    `gravity_reference` se interpreta como magnitud positiva; la comparación se
    realiza con |a| para que no dependa de si el eje vertical apunta hacia arriba
    o hacia abajo.
    """
    t = np.asarray(t, dtype=float)
    y = np.asarray(y, dtype=float)
    if t.ndim != 1 or y.ndim != 1 or len(t) != len(y) or len(t) < 5:
        raise ValueError("t e y deben ser vectores de igual longitud con al menos 5 puntos.")
    if not np.all(np.isfinite(t)) or not np.all(np.isfinite(y)) or np.any(np.diff(t) <= 0):
        raise ValueError("Los datos del ajuste deben ser finitos y el tiempo estrictamente creciente.")
    if gravity_reference <= 0:
        raise ValueError("La gravedad de referencia debe ser positiva.")
    initial = np.polyfit(t, y, 2)
    p0 = (float(initial[2]), float(initial[1]), float(2 * initial[0]))
    kwargs: dict[str, Any] = {"p0": p0, "maxfev": 20000}
    if sigma_y is not None:
        kwargs.update({"sigma": sigma_y, "absolute_sigma": True})
    parameters, covariance = curve_fit(free_fall_model, t, y, **kwargs)
    predicted = free_fall_model(t, *parameters)
    parameter_std = np.sqrt(np.maximum(np.diag(covariance), 0.0))
    metrics = _metrics(y, predicted)
    acceleration = float(parameters[2])
    relative_error = abs(abs(acceleration) - gravity_reference) / gravity_reference * 100.0
    return {
        "model": "free_fall_quadratic",
        "parameters": {"y0": float(parameters[0]), "v0": float(parameters[1]),
                       "acceleration": acceleration},
        "standard_errors": {"y0": float(parameter_std[0]), "v0": float(parameter_std[1]),
                             "acceleration": float(parameter_std[2])},
        "covariance": covariance.tolist(),
        "predicted": predicted,
        "residuals": y - predicted,
        "metrics": metrics,
        "gravity_reference": float(gravity_reference),
        "relative_gravity_error_percent": float(relative_error),
    }


def fit_linear(t: np.ndarray, values: np.ndarray) -> dict[str, Any]:
    """Ajusta una recta, útil como comprobación de ejes o movimiento uniforme."""
    t = np.asarray(t, dtype=float)
    values = np.asarray(values, dtype=float)
    if len(t) != len(values) or len(t) < 3 or np.any(np.diff(t) <= 0):
        raise ValueError("Se requieren vectores compatibles y tiempos crecientes.")
    parameters, covariance = curve_fit(linear_model, t, values)
    predicted = linear_model(t, *parameters)
    errors = np.sqrt(np.maximum(np.diag(covariance), 0.0))
    return {"parameters": {"intercept": float(parameters[0]), "slope": float(parameters[1])},
            "standard_errors": {"intercept": float(errors[0]), "slope": float(errors[1])},
            "predicted": predicted, "residuals": values - predicted,
            "metrics": _metrics(values, predicted)}
