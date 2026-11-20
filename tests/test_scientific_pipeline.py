"""Pruebas con funciones analíticas conocidas y datos sintéticos."""
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from src.data_loader import DataValidationError, load_tracker_data
from src.kinematics import calculate_kinematics
from src.curve_fitting import detect_quadratic_outliers, fit_free_fall


class KinematicsTests(unittest.TestCase):
    def test_constant_acceleration_derivatives(self) -> None:
        t = np.linspace(0.0, 2.0, 201)
        acceleration, velocity_0, position_0 = 3.2, -0.4, 1.5
        x = position_0 + velocity_0 * t + 0.5 * acceleration * t ** 2
        data = pd.DataFrame({"t": t, "x": np.zeros_like(t), "y": x})
        result = calculate_kinematics(data, smoothing="none", sigma_position=0.0)
        np.testing.assert_allclose(result["ay"].iloc[2:-2], acceleration, atol=1e-8)
        np.testing.assert_allclose(result["vy"].iloc[2:-2], velocity_0 + acceleration * t[2:-2], atol=1e-8)

    def test_free_fall_fit_recovers_parameters(self) -> None:
        t = np.linspace(0.0, 1.5, 100)
        y = 0.8 + 0.25 * t + 0.5 * 9.79 * t ** 2
        fit = fit_free_fall(t, y, gravity_reference=9.81)
        self.assertAlmostEqual(fit["parameters"]["acceleration"], 9.79, places=7)
        self.assertGreater(fit["metrics"]["r_squared"], 0.999999)

    def test_tracker_csv_header_mapping_and_row_drop(self) -> None:
        content = "t (s),x (m),y (m)\n0,0,0\n0.1,0.1,0.2\n0.2,,0.5\n0.3,0.3,0.8\n0.4,0.4,1.1\n0.5,0.5,1.4\n"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "tracker.csv"
            path.write_text(content, encoding="utf-8")
            data, report = load_tracker_data(path)
        self.assertEqual(len(data), 5)
        self.assertEqual(report["dropped_rows"], 1)

    def test_duplicate_times_are_rejected(self) -> None:
        content = "t,x,y\n0,0,0\n0.1,1,1\n0.1,2,2\n0.2,3,3\n0.3,4,4\n0.4,5,5\n"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.csv"
            path.write_text(content, encoding="utf-8")
            with self.assertRaises(DataValidationError):
                load_tracker_data(path)

    def test_robust_outlier_screening_flags_spike_without_dropping_data(self) -> None:
        t = np.linspace(0, 1, 31)
        y = 0.2 + 0.1*t + 0.5*9.81*t**2
        y[15] += 0.3
        report = detect_quadratic_outliers(t, y, threshold=3.5)
        self.assertGreaterEqual(report["count"], 1)
        self.assertIn(15, np.flatnonzero(report["mask"]))


if __name__ == "__main__":
    unittest.main()
