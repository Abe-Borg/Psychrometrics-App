"""
Tests for the SHR line engine.

Covers SHR slope computation, line generation, ADP from SHR,
GSHR/ESHR calculations, edge cases, and SI units.
"""

import pytest
from app.config import UnitSystem, DEFAULT_PRESSURE_IP, DEFAULT_PRESSURE_SI
from app.engine.shr import (
    compute_shr_slope,
    generate_shr_line,
    find_adp_from_shr,
    calculate_shr_line,
    calculate_gshr,
)
from app.models.shr import SHRLineInput, GSHRInput


def approx(value: float, rel_tol: float = 0.01, abs_tol: float = 0.1):
    return pytest.approx(value, rel=rel_tol, abs=abs_tol)


# ---------------------------------------------------------------------------
# SHR slope computation
# ---------------------------------------------------------------------------

class TestSHRSlope:
    def test_slope_075_ip(self):
        """SHR=0.75, IP: slope = 0.244 × 0.25 / (1061 × 0.75) ≈ 7.67e-5"""
        slope = compute_shr_slope(0.75, UnitSystem.IP)
        expected = 0.244 * (1 - 0.75) / (1061.0 * 0.75)
        assert slope == approx(expected, rel_tol=0.001, abs_tol=1e-7)

    def test_slope_1_is_zero(self):
        """SHR=1.0 → slope=0 (horizontal line, pure sensible)."""
        slope = compute_shr_slope(1.0, UnitSystem.IP)
        assert slope == 0.0

    def test_slope_050_ip(self):
        """SHR=0.5: equal sensible and latent."""
        slope = compute_shr_slope(0.5, UnitSystem.IP)
        expected = 0.244 * 0.5 / (1061.0 * 0.5)
        assert slope == approx(expected, rel_tol=0.001, abs_tol=1e-7)

    def test_lower_shr_steeper_slope(self):
        """Lower SHR (more latent) → steeper slope."""
        slope_05 = compute_shr_slope(0.5, UnitSystem.IP)
        slope_08 = compute_shr_slope(0.8, UnitSystem.IP)
        assert slope_05 > slope_08

    def test_slope_si(self):
        """SI units: slope = 1.006 × (1-0.75) / (2501 × 0.75)."""
        slope = compute_shr_slope(0.75, UnitSystem.SI)
        expected = 1.006 * 0.25 / (2501.0 * 0.75)
        assert slope == approx(expected, rel_tol=0.001, abs_tol=1e-7)

    def test_invalid_shr_zero(self):
        with pytest.raises(ValueError, match="greater than 0"):
            compute_shr_slope(0.0, UnitSystem.IP)

    def test_invalid_shr_above_one(self):
        with pytest.raises(ValueError, match="not exceed"):
            compute_shr_slope(1.5, UnitSystem.IP)


# ---------------------------------------------------------------------------
# SHR line generation
# ---------------------------------------------------------------------------

class TestSHRLineGeneration:
    def test_line_has_points(self):
        """Line should have multiple points."""
        slope = compute_shr_slope(0.75, UnitSystem.IP)
        points = generate_shr_line(75.0, 0.0093, slope, DEFAULT_PRESSURE_IP, UnitSystem.IP)
        assert len(points) > 10

    def test_line_passes_through_room(self):
        """Room point should be on the line (approximately)."""
        room_Tdb, room_W = 75.0, 0.0093
        slope = compute_shr_slope(0.75, UnitSystem.IP)
        points = generate_shr_line(room_Tdb, room_W, slope, DEFAULT_PRESSURE_IP, UnitSystem.IP)

        # Find point closest to room Tdb
        closest = min(points, key=lambda p: abs(p.Tdb - room_Tdb))
        assert closest.Tdb == approx(room_Tdb, abs_tol=2.0)

    def test_line_below_saturation(self):
        """All points should have W ≤ W_sat (within tolerance)."""
        import psychrolib
        psychrolib.SetUnitSystem(psychrolib.IP)
        slope = compute_shr_slope(0.75, UnitSystem.IP)
        points = generate_shr_line(75.0, 0.0093, slope, DEFAULT_PRESSURE_IP, UnitSystem.IP)

        for p in points:
            W_sat = psychrolib.GetSatHumRatio(p.Tdb, DEFAULT_PRESSURE_IP)
            assert p.W <= W_sat * 1.02  # 2% tolerance

    def test_shr_1_horizontal(self):
        """SHR=1.0 → horizontal line (constant W)."""
        slope = compute_shr_slope(1.0, UnitSystem.IP)
        points = generate_shr_line(75.0, 0.0093, slope, DEFAULT_PRESSURE_IP, UnitSystem.IP)
        # All points should have approximately the same W
        for p in points:
            assert p.W == approx(0.0093, abs_tol=0.0001)


# ---------------------------------------------------------------------------
# ADP from SHR line
# ---------------------------------------------------------------------------

class TestADPFromSHR:
    def test_adp_found(self):
        """ADP should be found for typical conditions."""
        slope = compute_shr_slope(0.75, UnitSystem.IP)
        adp_Tdb = find_adp_from_shr(75.0, 0.0093, slope, DEFAULT_PRESSURE_IP, UnitSystem.IP)
        assert 30.0 < adp_Tdb < 75.0

    def test_adp_below_room(self):
        """ADP Tdb must be less than room Tdb."""
        slope = compute_shr_slope(0.75, UnitSystem.IP)
        adp_Tdb = find_adp_from_shr(75.0, 0.0093, slope, DEFAULT_PRESSURE_IP, UnitSystem.IP)
        assert adp_Tdb < 75.0

    def test_adp_on_saturation(self):
        """ADP should lie on the saturation curve."""
        import psychrolib
        psychrolib.SetUnitSystem(psychrolib.IP)
        slope = compute_shr_slope(0.75, UnitSystem.IP)
        adp_Tdb = find_adp_from_shr(75.0, 0.0093, slope, DEFAULT_PRESSURE_IP, UnitSystem.IP)

        W_sat = psychrolib.GetSatHumRatio(adp_Tdb, DEFAULT_PRESSURE_IP)
        W_line = 0.0093 + slope * (adp_Tdb - 75.0)
        assert W_sat == approx(W_line, abs_tol=0.0001)

    def test_adp_shr_1(self):
        """SHR=1.0 (horizontal line) → ADP is at the dew point."""
        import psychrolib
        psychrolib.SetUnitSystem(psychrolib.IP)
        slope = compute_shr_slope(1.0, UnitSystem.IP)
        adp_Tdb = find_adp_from_shr(75.0, 0.0093, slope, DEFAULT_PRESSURE_IP, UnitSystem.IP)
        # ADP should be near the dew point
        Tdp = psychrolib.GetTDewPointFromHumRatio(75.0, 0.0093, DEFAULT_PRESSURE_IP)
        assert adp_Tdb == approx(Tdp, abs_tol=1.0)


# ---------------------------------------------------------------------------
# Full SHR line calculation via API model
# ---------------------------------------------------------------------------

class TestCalculateSHRLine:
    def setup_method(self):
        self.result = calculate_shr_line(SHRLineInput(
            unit_system=UnitSystem.IP,
            pressure=DEFAULT_PRESSURE_IP,
            room_pair=("Tdb", "RH"),
            room_values=(75.0, 50.0),
            shr=0.75,
        ))

    def test_shr_value(self):
        assert self.result.shr == 0.75

    def test_slope_positive(self):
        assert self.result.slope_dW_dTdb > 0

    def test_line_has_points(self):
        assert len(self.result.line_points) > 10

    def test_adp_reasonable(self):
        assert 30.0 < self.result.adp_Tdb < 75.0

    def test_adp_is_saturated(self):
        assert self.result.adp["RH"] == approx(100.0, abs_tol=0.1)

    def test_room_point_resolved(self):
        assert self.result.room_point["Tdb"] == approx(75.0)
        assert self.result.room_point["RH"] == approx(50.0)


# ---------------------------------------------------------------------------
# GSHR calculation
# ---------------------------------------------------------------------------

class TestGSHR:
    """
    Standard AHU scenario:
    Room: 75°F, 50% RH
    OA: 95°F, 75°F wb
    Room loads: Qs=60000 BTU/hr, Qt=80000 BTU/hr (SHR=0.75)
    OA fraction: 0.20, total airflow: 2000 CFM
    """

    def setup_method(self):
        self.result = calculate_gshr(GSHRInput(
            unit_system=UnitSystem.IP,
            pressure=DEFAULT_PRESSURE_IP,
            room_pair=("Tdb", "RH"),
            room_values=(75.0, 50.0),
            oa_pair=("Tdb", "Twb"),
            oa_values=(95.0, 75.0),
            room_sensible_load=60000.0,
            room_total_load=80000.0,
            oa_fraction=0.20,
            total_airflow=2000.0,
        ))

    def test_room_shr(self):
        assert self.result.room_shr == approx(0.75, abs_tol=0.01)

    def test_gshr_differs_from_room_shr(self):
        """GSHR should differ from room SHR due to OA load."""
        assert self.result.gshr != self.result.room_shr

    def test_gshr_in_range(self):
        assert 0.0 < self.result.gshr < 1.0

    def test_room_shr_line_has_points(self):
        assert len(self.result.room_shr_line) > 5

    def test_gshr_line_has_points(self):
        assert len(self.result.gshr_line) > 5

    def test_mixed_point_between(self):
        """Mixed point Tdb should be between room and OA."""
        mixed_Tdb = self.result.mixed_point["Tdb"]
        assert 75.0 <= mixed_Tdb <= 95.0

    def test_room_shr_adp(self):
        assert self.result.room_shr_adp["RH"] == approx(100.0, abs_tol=0.1)

    def test_gshr_adp(self):
        assert self.result.gshr_adp["RH"] == approx(100.0, abs_tol=0.1)

    def test_no_eshr_without_bf(self):
        assert self.result.eshr is None
        assert self.result.eshr_line is None


# ---------------------------------------------------------------------------
# ESHR (with bypass factor)
# ---------------------------------------------------------------------------

class TestESHR:
    def setup_method(self):
        self.result = calculate_gshr(GSHRInput(
            unit_system=UnitSystem.IP,
            pressure=DEFAULT_PRESSURE_IP,
            room_pair=("Tdb", "RH"),
            room_values=(75.0, 50.0),
            oa_pair=("Tdb", "Twb"),
            oa_values=(95.0, 75.0),
            room_sensible_load=60000.0,
            room_total_load=80000.0,
            oa_fraction=0.20,
            total_airflow=2000.0,
            bypass_factor=0.15,
        ))

    def test_eshr_computed(self):
        assert self.result.eshr is not None

    def test_eshr_differs_from_gshr(self):
        assert self.result.eshr != self.result.gshr

    def test_eshr_line_has_points(self):
        assert self.result.eshr_line is not None
        assert len(self.result.eshr_line) > 5

    def test_eshr_adp_saturated(self):
        assert self.result.eshr_adp is not None
        assert self.result.eshr_adp["RH"] == approx(100.0, abs_tol=0.1)


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestSHREdgeCases:
    def test_shr_too_low(self):
        with pytest.raises(ValueError):
            calculate_shr_line(SHRLineInput(
                room_pair=("Tdb", "RH"),
                room_values=(75.0, 50.0),
                shr=0.0,
            ))

    def test_shr_too_high(self):
        with pytest.raises(ValueError):
            calculate_shr_line(SHRLineInput(
                room_pair=("Tdb", "RH"),
                room_values=(75.0, 50.0),
                shr=1.5,
            ))

    def test_sensible_exceeds_total(self):
        with pytest.raises(ValueError, match="cannot exceed"):
            calculate_gshr(GSHRInput(
                room_pair=("Tdb", "RH"),
                room_values=(75.0, 50.0),
                oa_pair=("Tdb", "RH"),
                oa_values=(95.0, 50.0),
                room_sensible_load=100000.0,
                room_total_load=80000.0,
                oa_fraction=0.20,
                total_airflow=2000.0,
            ))


# ---------------------------------------------------------------------------
# SI units
# ---------------------------------------------------------------------------

class TestSHRSI:
    def setup_method(self):
        self.result = calculate_shr_line(SHRLineInput(
            unit_system=UnitSystem.SI,
            pressure=DEFAULT_PRESSURE_SI,
            room_pair=("Tdb", "RH"),
            room_values=(24.0, 50.0),
            shr=0.75,
        ))

    def test_unit_system(self):
        assert self.result.room_point["unit_system"] == "SI"

    def test_slope_positive(self):
        assert self.result.slope_dW_dTdb > 0

    def test_adp_reasonable(self):
        assert -5.0 < self.result.adp_Tdb < 24.0

    def test_line_has_points(self):
        assert len(self.result.line_points) > 10
