"""
Tests for the chart background data generator.

Validates that all line generators produce reasonable output:
- Correct number of line sets
- Sufficient points per line
- Values within expected ranges
- Monotonic behavior where expected
- Saturation curve matches psychrolib direct calls
"""

import pytest
import psychrolib

from app.config import UnitSystem, DEFAULT_PRESSURE_IP, DEFAULT_PRESSURE_SI, GRAINS_PER_LB
from app.engine.chart_generator import (
    generate_saturation_curve,
    generate_rh_lines,
    generate_twb_lines,
    generate_enthalpy_lines,
    generate_volume_lines,
    generate_chart_data,
)


# ---------------------------------------------------------------------------
# Saturation Curve
# ---------------------------------------------------------------------------

class TestSaturationCurve:
    def setup_method(self):
        self.points = generate_saturation_curve(DEFAULT_PRESSURE_IP, UnitSystem.IP)

    def test_has_points(self):
        assert len(self.points) > 100

    def test_tdb_range(self):
        tdbs = [p["Tdb"] for p in self.points]
        assert min(tdbs) <= 25.0  # near chart min
        assert max(tdbs) >= 115.0  # near chart max

    def test_w_increases_with_tdb(self):
        """Saturation humidity ratio should increase with temperature."""
        for i in range(1, len(self.points)):
            assert self.points[i]["W"] >= self.points[i - 1]["W"]

    def test_spot_check_against_psychrolib(self):
        """Verify a few points against direct psychrolib calls."""
        psychrolib.SetUnitSystem(psychrolib.IP)
        for Tdb_check in [40.0, 60.0, 80.0, 100.0]:
            W_expected = psychrolib.GetSatHumRatio(Tdb_check, DEFAULT_PRESSURE_IP)
            # Find the closest point in our curve
            closest = min(self.points, key=lambda p: abs(p["Tdb"] - Tdb_check))
            assert abs(closest["W"] - W_expected) < 0.001

    def test_w_display_is_grains(self):
        """W_display should be in grains (W * 7000) for IP."""
        for p in self.points[:5]:
            expected_grains = p["W"] * GRAINS_PER_LB
            assert abs(p["W_display"] - expected_grains) < 0.1


# ---------------------------------------------------------------------------
# Constant RH Lines
# ---------------------------------------------------------------------------

class TestRhLines:
    def setup_method(self):
        self.lines = generate_rh_lines(DEFAULT_PRESSURE_IP, UnitSystem.IP)

    def test_expected_rh_values(self):
        expected = {"10", "20", "30", "40", "50", "60", "70", "80", "90"}
        assert set(self.lines.keys()) == expected

    def test_each_line_has_points(self):
        for rh, points in self.lines.items():
            assert len(points) > 50, f"RH {rh}% line has too few points"

    def test_higher_rh_means_higher_w_at_same_tdb(self):
        """At the same Tdb, higher RH should give higher W."""
        # Compare 30% and 70% at a common Tdb
        line_30 = {round(p["Tdb"]): p["W"] for p in self.lines["30"]}
        line_70 = {round(p["Tdb"]): p["W"] for p in self.lines["70"]}
        common_tdbs = set(line_30.keys()) & set(line_70.keys())
        assert len(common_tdbs) > 10
        for tdb in common_tdbs:
            assert line_70[tdb] > line_30[tdb]

    def test_all_w_positive(self):
        for rh, points in self.lines.items():
            for p in points:
                assert p["W"] >= 0

    def test_rh_lines_below_saturation(self):
        """Every RH line should have W values below the saturation curve."""
        psychrolib.SetUnitSystem(psychrolib.IP)
        for rh, points in self.lines.items():
            for p in points[:10]:  # spot check first 10
                W_sat = psychrolib.GetSatHumRatio(p["Tdb"], DEFAULT_PRESSURE_IP)
                assert p["W"] <= W_sat + 0.0001


# ---------------------------------------------------------------------------
# Constant Wet-Bulb Lines
# ---------------------------------------------------------------------------

class TestTwbLines:
    def setup_method(self):
        self.lines = generate_twb_lines(DEFAULT_PRESSURE_IP, UnitSystem.IP)

    def test_has_lines(self):
        assert len(self.lines) >= 8  # at least 8 Twb lines

    def test_each_line_has_points(self):
        for twb, points in self.lines.items():
            assert len(points) >= 2, f"Twb {twb} line has too few points"

    def test_w_decreases_as_tdb_increases(self):
        """Along a constant Twb line, W should decrease as Tdb increases."""
        for twb, points in self.lines.items():
            for i in range(1, len(points)):
                if points[i]["Tdb"] > points[i - 1]["Tdb"]:
                    assert points[i]["W"] <= points[i - 1]["W"] + 0.0001, (
                        f"Twb {twb}: W increased from {points[i-1]} to {points[i]}"
                    )

    def test_line_starts_near_saturation(self):
        """Each Twb line should start near the saturation curve (Tdb ≈ Twb)."""
        for twb, points in self.lines.items():
            first_tdb = points[0]["Tdb"]
            assert abs(first_tdb - float(twb)) < 2.0, (
                f"Twb {twb} line starts at Tdb={first_tdb}, expected near {twb}"
            )


# ---------------------------------------------------------------------------
# Constant Enthalpy Lines
# ---------------------------------------------------------------------------

class TestEnthalpyLines:
    def setup_method(self):
        self.lines = generate_enthalpy_lines(DEFAULT_PRESSURE_IP, UnitSystem.IP)

    def test_has_lines(self):
        assert len(self.lines) >= 5

    def test_each_line_has_points(self):
        for h, points in self.lines.items():
            assert len(points) >= 2, f"Enthalpy {h} line has too few points"

    def test_w_decreases_as_tdb_increases(self):
        """Along a constant enthalpy line, W should decrease as Tdb increases."""
        for h, points in self.lines.items():
            for i in range(1, len(points)):
                if points[i]["Tdb"] > points[i - 1]["Tdb"]:
                    assert points[i]["W"] <= points[i - 1]["W"] + 0.0001

    def test_enthalpy_spot_check(self):
        """Verify a point on the h=30 line against direct calculation."""
        psychrolib.SetUnitSystem(psychrolib.IP)
        if "30" in self.lines:
            mid = self.lines["30"][len(self.lines["30"]) // 2]
            h_calc = psychrolib.GetMoistAirEnthalpy(mid["Tdb"], mid["W"])
            assert abs(h_calc - 30.0) < 0.5


# ---------------------------------------------------------------------------
# Constant Volume Lines
# ---------------------------------------------------------------------------

class TestVolumeLines:
    def setup_method(self):
        self.lines = generate_volume_lines(DEFAULT_PRESSURE_IP, UnitSystem.IP)

    def test_has_lines(self):
        assert len(self.lines) >= 3

    def test_each_line_has_points(self):
        for v, points in self.lines.items():
            assert len(points) >= 2, f"Volume {v} line has too few points"

    def test_volume_spot_check(self):
        """Verify a point against direct psychrolib calculation."""
        psychrolib.SetUnitSystem(psychrolib.IP)
        for v_label, points in self.lines.items():
            if len(points) > 5:
                mid = points[len(points) // 2]
                v_calc = psychrolib.GetMoistAirVolume(mid["Tdb"], mid["W"], DEFAULT_PRESSURE_IP)
                assert abs(v_calc - float(v_label)) < 0.05, (
                    f"Volume line {v_label}: expected {v_label}, got {v_calc:.3f} "
                    f"at Tdb={mid['Tdb']}, W={mid['W']}"
                )
                break  # one check is enough


# ---------------------------------------------------------------------------
# Full Chart Data
# ---------------------------------------------------------------------------

class TestFullChartData:
    def setup_method(self):
        self.data = generate_chart_data(DEFAULT_PRESSURE_IP, UnitSystem.IP)

    def test_has_all_sections(self):
        assert "saturation_curve" in self.data
        assert "rh_lines" in self.data
        assert "twb_lines" in self.data
        assert "enthalpy_lines" in self.data
        assert "volume_lines" in self.data
        assert "ranges" in self.data
        assert "unit_system" in self.data
        assert "pressure" in self.data

    def test_unit_system(self):
        assert self.data["unit_system"] == "IP"

    def test_pressure(self):
        assert self.data["pressure"] == DEFAULT_PRESSURE_IP

    def test_ranges(self):
        assert self.data["ranges"]["Tdb_min"] == 20.0
        assert self.data["ranges"]["Tdb_max"] == 120.0


# ---------------------------------------------------------------------------
# SI Unit System
# ---------------------------------------------------------------------------

class TestChartDataSI:
    def setup_method(self):
        self.data = generate_chart_data(DEFAULT_PRESSURE_SI, UnitSystem.SI)

    def test_has_all_sections(self):
        assert "saturation_curve" in self.data
        assert "rh_lines" in self.data
        assert "twb_lines" in self.data
        assert "enthalpy_lines" in self.data
        assert "volume_lines" in self.data

    def test_si_saturation_curve(self):
        points = self.data["saturation_curve"]
        assert len(points) > 100
        # W_display should be in g/kg for SI
        for p in points[:5]:
            assert abs(p["W_display"] - p["W"] * 1000.0) < 0.1

    def test_si_rh_lines(self):
        assert len(self.data["rh_lines"]) == 9


# ---------------------------------------------------------------------------
# Altitude / Non-standard Pressure
# ---------------------------------------------------------------------------

class TestNonStandardPressure:
    """Chart data at Denver altitude (~12.1 psia)."""

    def setup_method(self):
        self.data = generate_chart_data(12.1, UnitSystem.IP)

    def test_saturation_higher_than_sea_level(self):
        """At lower pressure, saturation W should be higher at the same Tdb."""
        sea_level = generate_saturation_curve(DEFAULT_PRESSURE_IP, UnitSystem.IP)
        denver = self.data["saturation_curve"]

        # Compare W at ~80°F
        sl_80 = min(sea_level, key=lambda p: abs(p["Tdb"] - 80.0))
        dn_80 = min(denver, key=lambda p: abs(p["Tdb"] - 80.0))
        assert dn_80["W"] > sl_80["W"], (
            f"At 80°F, Denver W ({dn_80['W']}) should exceed sea level W ({sl_80['W']})"
        )
