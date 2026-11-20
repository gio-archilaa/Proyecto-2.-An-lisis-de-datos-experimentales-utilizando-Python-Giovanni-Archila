"""Orquestador del pipeline completo Tracker -> Python -> figuras -> LaTeX."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

from src.data_loader import load_tracker_data
from src.kinematics import calculate_kinematics
from src.curve_fitting import detect_quadratic_outliers, fit_free_fall
from src.plotting import create_publication_plots

ROOT = Path(__file__).resolve().parents[1]


def _write_latex_values(result: dict, output_dir: Path) -> None:
    """Escribe macros y tabla de resultados que `report/main.tex` incorpora."""
    output_dir.mkdir(parents=True, exist_ok=True)
    p = result["fit"]["parameters"]
    u = result["fit"]["standard_errors"]
    m = result["fit"]["metrics"]
    def number(value: float, digits: int = 4) -> str:
        return f"{value:.{digits}f}"
    macros = [
        "% Archivo generado automáticamente por src/main.py; no editar manualmente.",
        f"\\newcommand{{\\MeasuredAcceleration}}{{{number(p['acceleration'])}}}",
        f"\\newcommand{{\\AccelerationUncertainty}}{{{number(u['acceleration'])}}}",
        f"\\newcommand{{\\FitRSquared}}{{{number(m['r_squared'], 5)}}}",
        f"\\newcommand{{\\FitRMSE}}{{{number(m['rmse'], 5)}}}",
        f"\\newcommand{{\\GravityRelativeError}}{{{number(result['fit']['relative_gravity_error_percent'], 3)}}}",
        f"\\newcommand{{\\ValidDataPoints}}{{{result['cleaning']['valid_rows']}}}",
        f"\\newcommand{{\\DroppedDataPoints}}{{{result['cleaning']['dropped_rows']}}}",
        "",
    ]
    (output_dir / "results.tex").write_text("\n".join(macros), encoding="utf-8")
    table = r"""%% Tabla generada automáticamente por src/main.py.
\begin{table}[htbp]
\centering
\caption{Parámetros del ajuste de caída libre y métricas de calidad.}
\label{tab:fit-results}
\begin{tabular}{lrr}
\hline
Parámetro & Valor & Incertidumbre estándar \\
\hline
Posición inicial $y_0$ (m) & %(y0)s & %(uy0)s \\
Velocidad inicial $v_0$ (m/s) & %(v0)s & %(uv0)s \\
Aceleración $a_y$ (m/s$^2$) & %(a)s & %(ua)s \\
$R^2$ & %(r2)s & -- \\
RMSE (m) & %(rmse)s & -- \\
Error relativo frente a $g$ (\%%) & %(err)s & -- \\
\hline
\end{tabular}
\end{table}
""" % {
        "y0": number(p["y0"]), "uy0": number(u["y0"]),
        "v0": number(p["v0"]), "uv0": number(u["v0"]),
        "a": number(p["acceleration"]), "ua": number(u["acceleration"]),
        "r2": number(m["r_squared"], 5), "rmse": number(m["rmse"], 5),
        "err": number(result["fit"]["relative_gravity_error_percent"], 3),
    }
    (output_dir / "results_table.tex").write_text(table, encoding="utf-8")


def run_pipeline(input_path: str | Path, *, smoothing: str = "savgol", window: int = 9,
                 polyorder: int = 2, sigma_position: float = 0.005,
                 sigma_scale_relative: float = 0.0, gravity_reference: float = 9.81) -> dict:
    """Ejecuta limpieza, cinemática, ajuste, gráficos y salidas para el informe."""
    source = Path(input_path)
    if not source.is_absolute():
        source = ROOT / source
    processed_dir = ROOT / "data" / "processed"
    figures_dir = ROOT / "report" / "figures"
    generated_dir = ROOT / "report" / "generated"
    processed_dir.mkdir(parents=True, exist_ok=True)
    raw, cleaning = load_tracker_data(source)
    processed = calculate_kinematics(raw, smoothing=smoothing, window=window,
                                      polyorder=polyorder, sigma_position=sigma_position)
    processed_path = processed_dir / f"{source.stem}_processed.csv"
    processed.to_csv(processed_path, index=False)

    outliers = detect_quadratic_outliers(raw["t"].to_numpy(), raw["y"].to_numpy())
    sigma_y = np.sqrt(sigma_position ** 2 + (np.abs(raw["y"].to_numpy()) * sigma_scale_relative) ** 2)
    fit = fit_free_fall(raw["t"].to_numpy(), raw["y"].to_numpy(),
                        sigma_y=sigma_y if np.any(sigma_y > 0) else None,
                        gravity_reference=gravity_reference)
    result = {
        "input_file": str(source.relative_to(ROOT)) if source.is_relative_to(ROOT) else source.name,
        "cleaning": cleaning,
        "outlier_screening": {"count": outliers["count"], "threshold_mad": outliers["threshold"],
                              "robust_sigma_m": outliers["robust_sigma"],
                              "indices": np.flatnonzero(outliers["mask"]).tolist()},
        "settings": {"smoothing": smoothing, "window": window, "polyorder": polyorder,
                     "sigma_position_m": sigma_position, "sigma_scale_relative": sigma_scale_relative,
                     "gravity_reference_m_s2": gravity_reference},
        "fit": {key: value for key, value in fit.items() if key not in {"predicted", "residuals", "covariance"}},
        "processed_file": str(processed_path.relative_to(ROOT)),
    }
    plots = create_publication_plots(processed, fit, figures_dir, gravity_reference=gravity_reference)
    result["figures"] = [str(path.relative_to(ROOT)) for path in plots]
    summary_path = generated_dir / "results.json"
    generated_dir.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    _write_latex_values(result, generated_dir)
    result["summary_file"] = str(summary_path.relative_to(ROOT))
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Pipeline de análisis experimental de Tracker.")
    parser.add_argument("--input", default="data/raw/caida_libre_tracker.csv",
                        help="Ruta a CSV/TXT exportado de Tracker (relativa al proyecto o absoluta).")
    parser.add_argument("--smoothing", choices=["savgol", "moving", "none"], default="savgol")
    parser.add_argument("--window", type=int, default=9,
                        help="Ventana impar de suavizado (se adapta si supera el número de puntos).")
    parser.add_argument("--polyorder", type=int, default=2)
    parser.add_argument("--sigma-position", type=float, default=0.005,
                        help="Incertidumbre estándar de posición en metros.")
    parser.add_argument("--sigma-scale-relative", type=float, default=0.0,
                        help="Incertidumbre relativa de calibración de escala (por ejemplo 0.005 = 0.5%%).")
    parser.add_argument("--gravity", type=float, default=9.81,
                        help="Magnitud de la gravedad de referencia en m/s².")
    args = parser.parse_args()
    try:
        result = run_pipeline(args.input, smoothing=args.smoothing, window=args.window,
                              polyorder=args.polyorder, sigma_position=args.sigma_position,
                              sigma_scale_relative=args.sigma_scale_relative, gravity_reference=args.gravity)
    except (FileNotFoundError, ValueError, RuntimeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    p = result["fit"]["parameters"]
    uncertainty = result["fit"]["standard_errors"]["acceleration"]
    print("\nANÁLISIS COMPLETADO")
    print(f"Puntos válidos: {result['cleaning']['valid_rows']} | descartados: {result['cleaning']['dropped_rows']}")
    print(f"Aceleración ajustada: {p['acceleration']:.5f} ± {uncertainty:.5f} m/s²")
    print(f"R²: {result['fit']['metrics']['r_squared']:.6f}")
    print(f"Error relativo frente a g: {result['fit']['relative_gravity_error_percent']:.3f} %")
    print(f"Datos procesados: {result['processed_file']}")
    print(f"Resultados LaTeX: {result['summary_file']} y report/generated/results_table.tex")
    print("Figuras: report/figures/")
    print("Para compilar el informe: cd report && pdflatex main.tex && bibtex main && pdflatex main.tex && pdflatex main.tex")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
