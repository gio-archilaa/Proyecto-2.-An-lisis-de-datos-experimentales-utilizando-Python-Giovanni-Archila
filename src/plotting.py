"""Gráficas científicas de alta resolución para el informe."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def _save(fig: plt.Figure, output_dir: Path, stem: str) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(output_dir / f"{stem}.png", dpi=300, bbox_inches="tight")
    fig.savefig(output_dir / f"{stem}.pdf", bbox_inches="tight")
    plt.close(fig)


def create_publication_plots(data: pd.DataFrame, fit: dict[str, Any], output_dir: str | Path,
                             *, gravity_reference: float = 9.81) -> list[Path]:
    """Crea posición, velocidad, aceleración y residuos (PNG 300 DPI + PDF)."""
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    t = data["t"].to_numpy()
    outputs: list[Path] = []

    fig, ax = plt.subplots(figsize=(7.2, 4.8))
    ax.scatter(t, data["x"], s=14, alpha=0.55, label="x experimental")
    ax.plot(t, data["x_smooth"], linewidth=1.5, label="x suavizada")
    ax.scatter(t, data["y"], s=14, alpha=0.55, label="y experimental")
    ax.plot(t, data["y_smooth"], linewidth=1.5, label="y suavizada")
    ax.plot(t, fit["predicted"], linestyle="--", linewidth=1.8, label="ajuste cuadrático de y")
    ax.set(xlabel="Tiempo, t (s)", ylabel="Posición (m)", title="Posición vs. tiempo")
    ax.grid(True, alpha=0.25)
    ax.legend()
    _save(fig, destination, "posicion_tiempo")
    outputs.extend([destination / "posicion_tiempo.png", destination / "posicion_tiempo.pdf"])

    fig, ax = plt.subplots(figsize=(7.2, 4.8))
    ax.plot(t, data["vx"], label="$v_x$", linewidth=1.5)
    ax.plot(t, data["vy"], label="$v_y$", linewidth=1.5)
    sigma_v = float(data["sigma_velocity"].iloc[0])
    ax.fill_between(t, data["vy"] - sigma_v, data["vy"] + sigma_v, alpha=0.18,
                    label="incertidumbre aproximada de $v_y$")
    ax.set(xlabel="Tiempo, t (s)", ylabel="Velocidad (m/s)", title="Velocidad vs. tiempo")
    ax.grid(True, alpha=0.25)
    ax.legend()
    _save(fig, destination, "velocidad_tiempo")
    outputs.extend([destination / "velocidad_tiempo.png", destination / "velocidad_tiempo.pdf"])

    fig, ax = plt.subplots(figsize=(7.2, 4.8))
    ax.plot(t, data["ax"], label="$a_x$", linewidth=1.5)
    ax.plot(t, data["ay"], label="$a_y$ experimental", linewidth=1.5)
    ax.axhline(gravity_reference, linestyle="--", label=f"referencia +{gravity_reference:.3f} m/s²")
    ax.axhline(-gravity_reference, linestyle=":", label=f"referencia −{gravity_reference:.3f} m/s²")
    sigma_a = float(data["sigma_acceleration"].iloc[0])
    ax.fill_between(t, data["ay"] - sigma_a, data["ay"] + sigma_a, alpha=0.16,
                    label="incertidumbre aproximada de $a_y$")
    ax.set(xlabel="Tiempo, t (s)", ylabel="Aceleración (m/s²)", title="Aceleración vs. tiempo")
    ax.grid(True, alpha=0.25)
    ax.legend(fontsize=8)
    _save(fig, destination, "aceleracion_tiempo")
    outputs.extend([destination / "aceleracion_tiempo.png", destination / "aceleracion_tiempo.pdf"])

    fig, ax = plt.subplots(figsize=(7.2, 4.8))
    ax.axhline(0, color="black", linewidth=1)
    ax.scatter(t, fit["residuals"], s=18, alpha=0.8)
    ax.set(xlabel="Tiempo, t (s)", ylabel="Residuo (m)", title="Residuos del ajuste cuadrático")
    ax.grid(True, alpha=0.25)
    _save(fig, destination, "residuos_ajuste")
    outputs.extend([destination / "residuos_ajuste.png", destination / "residuos_ajuste.pdf"])
    return outputs
