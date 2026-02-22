"""
Tests for the coil analysis engine.

Covers forward mode (ADP + BF → leaving), reverse mode (entering + leaving → ADP + BF),
round-trip consistency, absolute loads with airflow, GPM estimation, edge cases, and SI units.
"""

import pytest
from app.config import UnitSystem, DEFAULT_PRESSURE_IP, DEFAULT_PRESSURE_SI
from app.engine.coil import analyze_coil
from app.models.coil import CoilInput, CoilMode


def approx(value: float, rel_tol: float = 0.01, abs_tol: float = 0.1):
    return pytest.approx(value, rel=rel_tol, abs=abs_tol)


# ---------------------------------------------------------------------------
# Forward mode: ADP + BF → leaving state
# ---------------------------------------------------------------------------

class TestForwardCoil:
    """
    Forward mode: 80°F/67°F wb entering, ADP=45°F, BF=0.15.
    Expected leaving Tdb ≈ 50.25°F.
    """

    def setup_method(self):
        self.result = analyze_coil(CoilInput(
            mode=CoilMode.FORWARD,
            unit_system=UnitSystem.IP,
            pressure=DEFAULT_PRESSURE_IP,
            entering_pair=("Tdb", "Twb"),
            entering_values=(80.0, 67.0),
            adp_Tdb=45.0,
            bypass_factor=0.15,
        ))

    def test_leaving_tdb(self):
        assert self.result.leaving["Tdb"] == approx(50.25, abs_tol=0.5)

    def test_leaving_w_lower(self):
        assert self.result.leaving["W"] < self.result.entering["W"]

    def test_leaving_rh_high(self):
        assert self.result.leaving["RH"] > 80.0

    def test_mode(self):
        assert self.result.mode == CoilMode.FORWARD

    def test_adp_tdb(self):
        assert self.result.adp["Tdb"] == approx(45.0)

    def test_bypass_factor(self):
        assert self.result.bypass_factor == approx(0.15)

    def test_contact_factor(self):
        assert self.result.contact_factor == approx(0.85)

    def test_shr_in_range(self):
        assert 0.0 < self.result.SHR < 1.0

    def test_qt_positive(self):
        assert self.result.Qt > 0

    def test_qs_positive(self):
        assert self.result.Qs > 0

    def test_ql_positive(self):
        assert self.result.Ql > 0

    def test_qt_equals_qs_plus_ql(self):
        assert self.result.Qt == approx(self.result.Qs + self.result.Ql, abs_tol=0.05)

    def test_load_unit_per_mass(self):
        assert self.result.load_unit == "BTU/lb"

    def test_no_gpm_without_water(self):
        assert self.result.gpm is None

    def test_path_has_points(self):
        assert len(self.result.path_points) >= 2

    def test_no_warnings(self):
        assert len(self.result.warnings) == 0


# ---------------------------------------------------------------------------
# Reverse mode: entering + leaving → ADP + BF
# ---------------------------------------------------------------------------

class TestReverseCoil:
    """
    Reverse mode: 80°F/67°F wb entering, 55°F/90%RH leaving.
    Should back-calculate ADP and BF.
    """

    def setup_method(self):
        self.result = analyze_coil(CoilInput(
            mode=CoilMode.REVERSE,
            unit_system=UnitSystem.IP,
            pressure=DEFAULT_PRESSURE_IP,
            entering_pair=("Tdb", "Twb"),
            entering_values=(80.0, 67.0),
            leaving_pair=("Tdb", "RH"),
            leaving_values=(55.0, 90.0),
        ))

    def test_adp_tdb_reasonable(self):
        assert 35.0 < self.result.adp["Tdb"] < 55.0

    def test_bf_in_range(self):
        assert 0.0 < self.result.bypass_factor < 1.0

    def test_cf_complement(self):
        assert self.result.contact_factor == approx(1.0 - self.result.bypass_factor)

    def test_shr_in_range(self):
        assert 0.0 < self.result.SHR < 1.0

    def test_leaving_tdb(self):
        assert self.result.leaving["Tdb"] == approx(55.0)

    def test_mode(self):
        assert self.result.mode == CoilMode.REVERSE


# ---------------------------------------------------------------------------
# Round-trip: forward → reverse should recover ADP and BF
# ---------------------------------------------------------------------------

class TestRoundTrip:
    """Forward result fed into reverse should recover the same ADP and BF."""

    def setup_method(self):
        # Forward
        self.fwd = analyze_coil(CoilInput(
            mode=CoilMode.FORWARD,
            unit_system=UnitSystem.IP,
            pressure=DEFAULT_PRESSURE_IP,
            entering_pair=("Tdb", "Twb"),
            entering_values=(80.0, 67.0),
            adp_Tdb=45.0,
            bypass_factor=0.15,
        ))

        # Reverse using forward's leaving conditions
        leaving_Tdb = self.fwd.leaving["Tdb"]
        leaving_RH = self.fwd.leaving["RH"]
        self.rev = analyze_coil(CoilInput(
            mode=CoilMode.REVERSE,
            unit_system=UnitSystem.IP,
            pressure=DEFAULT_PRESSURE_IP,
            entering_pair=("Tdb", "Twb"),
            entering_values=(80.0, 67.0),
            leaving_pair=("Tdb", "RH"),
            leaving_values=(leaving_Tdb, leaving_RH),
        ))

    def test_adp_matches(self):
        assert self.rev.adp["Tdb"] == approx(self.fwd.adp["Tdb"], abs_tol=0.5)

    def test_bf_matches(self):
        assert self.rev.bypass_factor == approx(self.fwd.bypass_factor, abs_tol=0.02)

    def test_shr_matches(self):
        assert self.rev.SHR == approx(self.fwd.SHR, abs_tol=0.02)


# ---------------------------------------------------------------------------
# Absolute loads with airflow
# ---------------------------------------------------------------------------

class TestAbsoluteLoads:
    """Provide 1000 CFM → get BTU/hr loads."""

    def setup_method(self):
        self.result = analyze_coil(CoilInput(
            mode=CoilMode.FORWARD,
            unit_system=UnitSystem.IP,
            pressure=DEFAULT_PRESSURE_IP,
            entering_pair=("Tdb", "Twb"),
            entering_values=(80.0, 67.0),
            adp_Tdb=45.0,
            bypass_factor=0.15,
            airflow=1000.0,
        ))

    def test_load_unit_absolute(self):
        assert self.result.load_unit == "BTU/hr"

    def test_qt_large(self):
        """1000 CFM × ~30°F drop should be a substantial load."""
        assert self.result.Qt > 10000

    def test_qs_plus_ql_equals_qt(self):
        assert self.result.Qt == approx(self.result.Qs + self.result.Ql, abs_tol=10)


# ---------------------------------------------------------------------------
# GPM estimation
# ---------------------------------------------------------------------------

class TestGPMEstimation:
    """Provide airflow + water temps → get GPM."""

    def setup_method(self):
        self.result = analyze_coil(CoilInput(
            mode=CoilMode.FORWARD,
            unit_system=UnitSystem.IP,
            pressure=DEFAULT_PRESSURE_IP,
            entering_pair=("Tdb", "Twb"),
            entering_values=(80.0, 67.0),
            adp_Tdb=45.0,
            bypass_factor=0.15,
            airflow=1000.0,
            water_entering_temp=42.0,
            water_leaving_temp=55.0,
        ))

    def test_gpm_not_none(self):
        assert self.result.gpm is not None

    def test_gpm_positive(self):
        assert self.result.gpm > 0

    def test_gpm_reasonable(self):
        """For ~35,000 BTU/hr and 13°F ΔT: GPM ≈ Qt/(500×13) ≈ 5.4"""
        assert 1.0 < self.result.gpm < 20.0


class TestGPMWithoutAirflow:
    """GPM should be None when airflow is not provided."""

    def test_no_gpm_without_airflow(self):
        result = analyze_coil(CoilInput(
            mode=CoilMode.FORWARD,
            unit_system=UnitSystem.IP,
            pressure=DEFAULT_PRESSURE_IP,
            entering_pair=("Tdb", "Twb"),
            entering_values=(80.0, 67.0),
            adp_Tdb=45.0,
            bypass_factor=0.15,
            water_entering_temp=42.0,
            water_leaving_temp=55.0,
        ))
        assert result.gpm is None


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_forward_missing_adp(self):
        with pytest.raises(ValueError, match="adp_Tdb and bypass_factor"):
            analyze_coil(CoilInput(
                mode=CoilMode.FORWARD,
                entering_pair=("Tdb", "RH"),
                entering_values=(80.0, 50.0),
            ))

    def test_forward_bf_out_of_range(self):
        with pytest.raises(ValueError, match="between 0 and 1"):
            analyze_coil(CoilInput(
                mode=CoilMode.FORWARD,
                entering_pair=("Tdb", "RH"),
                entering_values=(80.0, 50.0),
                adp_Tdb=45.0,
                bypass_factor=1.5,
            ))

    def test_reverse_missing_leaving(self):
        with pytest.raises(ValueError, match="leaving_pair and leaving_values"):
            analyze_coil(CoilInput(
                mode=CoilMode.REVERSE,
                entering_pair=("Tdb", "RH"),
                entering_values=(80.0, 50.0),
            ))

    def test_reverse_leaving_tdb_higher(self):
        with pytest.raises(ValueError, match="must be less than"):
            analyze_coil(CoilInput(
                mode=CoilMode.REVERSE,
                entering_pair=("Tdb", "RH"),
                entering_values=(80.0, 50.0),
                leaving_pair=("Tdb", "RH"),
                leaving_values=(85.0, 40.0),
            ))

    def test_adp_above_dew_point_warns(self):
        result = analyze_coil(CoilInput(
            mode=CoilMode.FORWARD,
            entering_pair=("Tdb", "RH"),
            entering_values=(80.0, 30.0),  # low RH → high dew point gap
            adp_Tdb=60.0,  # above dew point of ~45°F at 30%RH
            bypass_factor=0.15,
        ))
        assert len(result.warnings) > 0
        assert "dew point" in result.warnings[0].lower()


# ---------------------------------------------------------------------------
# SI units
# ---------------------------------------------------------------------------

class TestCoilSI:
    """SI unit test: 27°C/19.5°C wb entering, ADP=7°C, BF=0.15."""

    def setup_method(self):
        self.result = analyze_coil(CoilInput(
            mode=CoilMode.FORWARD,
            unit_system=UnitSystem.SI,
            pressure=DEFAULT_PRESSURE_SI,
            entering_pair=("Tdb", "Twb"),
            entering_values=(27.0, 19.5),
            adp_Tdb=7.0,
            bypass_factor=0.15,
        ))

    def test_unit_system(self):
        assert self.result.unit_system == UnitSystem.SI

    def test_leaving_tdb(self):
        expected = 7.0 + 0.15 * (27.0 - 7.0)  # = 10.0°C
        assert self.result.leaving["Tdb"] == approx(expected, abs_tol=0.5)

    def test_load_unit(self):
        assert self.result.load_unit == "kJ/kg"

    def test_qt_positive(self):
        assert self.result.Qt > 0


# ---------------------------------------------------------------------------
# Arbitrary input pairs
# ---------------------------------------------------------------------------

class TestArbitraryPairs:
    """Test entering as Tdb+Tdp, leaving as Tdb+Twb."""

    def test_reverse_with_tdb_tdp_entering(self):
        result = analyze_coil(CoilInput(
            mode=CoilMode.REVERSE,
            unit_system=UnitSystem.IP,
            pressure=DEFAULT_PRESSURE_IP,
            entering_pair=("Tdb", "Tdp"),
            entering_values=(80.0, 60.0),
            leaving_pair=("Tdb", "Twb"),
            leaving_values=(55.0, 54.0),
        ))
        assert 0.0 < result.bypass_factor < 1.0
        assert result.Qt > 0
