"""
Tests for the airflow and energy calculation engine.

Covers sensible/latent/total load equations, solve-for-any-variable,
altitude correction, condensation checking, SI units, and edge cases.
"""

import pytest
import psychrolib

from app.config import UnitSystem, DEFAULT_PRESSURE_IP, DEFAULT_PRESSURE_SI
from app.engine.airflow import calculate_airflow, check_condensation, compute_c_factor
from app.models.airflow import (
    AirflowCalcInput,
    CalcMode,
    CondensationCheckInput,
    LoadType,
)


def approx(value: float, rel_tol: float = 0.01, abs_tol: float = 0.1):
    return pytest.approx(value, rel=rel_tol, abs=abs_tol)


# ---------------------------------------------------------------------------
# C-factor computation
# ---------------------------------------------------------------------------

class TestCFactor:
    """Verify C-factor values at sea level standard conditions."""

    def test_sensible_c_at_sea_level_ip(self):
        """Cs ≈ 1.08 BTU/(hr·CFM·°F) at standard sea-level conditions."""
        C, rho = compute_c_factor(
            LoadType.SENSIBLE, 70.0, 0.01, DEFAULT_PRESSURE_IP, UnitSystem.IP
        )
        assert C == approx(1.08, rel_tol=0.02)

    def test_total_c_at_sea_level_ip(self):
        """Ct ≈ 4.5 at standard sea-level conditions."""
        C, rho = compute_c_factor(
            LoadType.TOTAL, 70.0, 0.01, DEFAULT_PRESSURE_IP, UnitSystem.IP
        )
        assert C == approx(4.5, rel_tol=0.02)

    def test_latent_c_at_sea_level_ip(self):
        """Cl ≈ 4760 at standard sea-level conditions."""
        C, rho = compute_c_factor(
            LoadType.LATENT, 70.0, 0.01, DEFAULT_PRESSURE_IP, UnitSystem.IP
        )
        assert C == approx(4760.0, rel_tol=0.02)

    def test_density_at_sea_level_ip(self):
        """Air density ≈ 0.075 lb/ft³ at sea level, 70°F."""
        _, rho = compute_c_factor(
            LoadType.SENSIBLE, 70.0, 0.01, DEFAULT_PRESSURE_IP, UnitSystem.IP
        )
        assert rho == approx(0.075, rel_tol=0.03, abs_tol=0.005)


# ---------------------------------------------------------------------------
# Sensible load calculations
# ---------------------------------------------------------------------------

class TestSensibleSolveQ:
    """Solve for Qs given CFM and ΔT at sea level."""

    def setup_method(self):
        self.result = calculate_airflow(AirflowCalcInput(
            calc_mode=CalcMode.SOLVE_Q,
            load_type=LoadType.SENSIBLE,
            unit_system=UnitSystem.IP,
            pressure=DEFAULT_PRESSURE_IP,
            airflow=1000.0,
            delta=20.0,
        ))

    def test_q_value(self):
        """Qs ≈ 1.08 × 1000 × 20 = 21,600 BTU/hr."""
        assert self.result.Q == approx(21600.0, rel_tol=0.02)

    def test_c_factor(self):
        assert self.result.C_factor == approx(1.08, rel_tol=0.02)

    def test_formula_contains_qs(self):
        assert "Qs" in self.result.formula

    def test_load_type(self):
        assert self.result.load_type == LoadType.SENSIBLE


class TestSensibleSolveCFM:
    """Solve for CFM given Qs and ΔT."""

    def setup_method(self):
        self.result = calculate_airflow(AirflowCalcInput(
            calc_mode=CalcMode.SOLVE_AIRFLOW,
            load_type=LoadType.SENSIBLE,
            unit_system=UnitSystem.IP,
            pressure=DEFAULT_PRESSURE_IP,
            Q=21600.0,
            delta=20.0,
        ))

    def test_airflow_value(self):
        """CFM ≈ 21600 / (1.08 × 20) ≈ 1000."""
        assert self.result.airflow == approx(1000.0, rel_tol=0.02)


class TestSensibleSolveDelta:
    """Solve for ΔT given Qs and CFM."""

    def setup_method(self):
        self.result = calculate_airflow(AirflowCalcInput(
            calc_mode=CalcMode.SOLVE_DELTA,
            load_type=LoadType.SENSIBLE,
            unit_system=UnitSystem.IP,
            pressure=DEFAULT_PRESSURE_IP,
            Q=21600.0,
            airflow=1000.0,
        ))

    def test_delta_value(self):
        """ΔT ≈ 21600 / (1.08 × 1000) ≈ 20."""
        assert self.result.delta == approx(20.0, rel_tol=0.02)


# ---------------------------------------------------------------------------
# Round-trip consistency
# ---------------------------------------------------------------------------

class TestRoundTrip:
    """Compute Q from airflow+delta, then solve back for each variable."""

    def setup_method(self):
        # First: solve for Q
        self.forward = calculate_airflow(AirflowCalcInput(
            calc_mode=CalcMode.SOLVE_Q,
            load_type=LoadType.SENSIBLE,
            unit_system=UnitSystem.IP,
            pressure=DEFAULT_PRESSURE_IP,
            airflow=2000.0,
            delta=15.0,
        ))

    def test_roundtrip_airflow(self):
        result = calculate_airflow(AirflowCalcInput(
            calc_mode=CalcMode.SOLVE_AIRFLOW,
            load_type=LoadType.SENSIBLE,
            unit_system=UnitSystem.IP,
            pressure=DEFAULT_PRESSURE_IP,
            Q=self.forward.Q,
            delta=15.0,
        ))
        assert result.airflow == approx(2000.0, rel_tol=0.001)

    def test_roundtrip_delta(self):
        result = calculate_airflow(AirflowCalcInput(
            calc_mode=CalcMode.SOLVE_DELTA,
            load_type=LoadType.SENSIBLE,
            unit_system=UnitSystem.IP,
            pressure=DEFAULT_PRESSURE_IP,
            Q=self.forward.Q,
            airflow=2000.0,
        ))
        assert result.delta == approx(15.0, rel_tol=0.001)


# ---------------------------------------------------------------------------
# Altitude correction (5000 ft / Denver)
# ---------------------------------------------------------------------------

class TestAltitudeCorrection:
    """At 5000 ft, density and C-factor are lower than sea level."""

    def setup_method(self):
        # Compute pressure at 5000 ft
        psychrolib.SetUnitSystem(psychrolib.IP)
        self.pressure_5000 = psychrolib.GetStandardAtmPressure(5000.0)

    def test_c_factor_lower_at_altitude(self):
        C_sea, _ = compute_c_factor(
            LoadType.SENSIBLE, 70.0, 0.01, DEFAULT_PRESSURE_IP, UnitSystem.IP
        )
        C_alt, _ = compute_c_factor(
            LoadType.SENSIBLE, 70.0, 0.01, self.pressure_5000, UnitSystem.IP
        )
        assert C_alt < C_sea

    def test_density_lower_at_altitude(self):
        _, rho_sea = compute_c_factor(
            LoadType.SENSIBLE, 70.0, 0.01, DEFAULT_PRESSURE_IP, UnitSystem.IP
        )
        _, rho_alt = compute_c_factor(
            LoadType.SENSIBLE, 70.0, 0.01, self.pressure_5000, UnitSystem.IP
        )
        assert rho_alt < rho_sea

    def test_more_cfm_needed_at_altitude(self):
        """Same load at altitude requires more airflow."""
        result_sea = calculate_airflow(AirflowCalcInput(
            calc_mode=CalcMode.SOLVE_AIRFLOW,
            load_type=LoadType.SENSIBLE,
            unit_system=UnitSystem.IP,
            pressure=DEFAULT_PRESSURE_IP,
            Q=21600.0,
            delta=20.0,
        ))
        result_alt = calculate_airflow(AirflowCalcInput(
            calc_mode=CalcMode.SOLVE_AIRFLOW,
            load_type=LoadType.SENSIBLE,
            unit_system=UnitSystem.IP,
            pressure=self.pressure_5000,
            Q=21600.0,
            delta=20.0,
        ))
        assert result_alt.airflow > result_sea.airflow


# ---------------------------------------------------------------------------
# Latent load calculations
# ---------------------------------------------------------------------------

class TestLatentCalc:
    """Latent load: Ql = Cl × CFM × ΔW."""

    def test_solve_q_latent(self):
        result = calculate_airflow(AirflowCalcInput(
            calc_mode=CalcMode.SOLVE_Q,
            load_type=LoadType.LATENT,
            unit_system=UnitSystem.IP,
            pressure=DEFAULT_PRESSURE_IP,
            airflow=1000.0,
            delta=0.005,   # ΔW in lb/lb
        ))
        # Ql ≈ 4760 × 1000 × 0.005 ≈ 23,800 BTU/hr
        assert result.Q == approx(23800.0, rel_tol=0.03)
        assert "Ql" in result.formula

    def test_solve_airflow_latent(self):
        result = calculate_airflow(AirflowCalcInput(
            calc_mode=CalcMode.SOLVE_AIRFLOW,
            load_type=LoadType.LATENT,
            unit_system=UnitSystem.IP,
            pressure=DEFAULT_PRESSURE_IP,
            Q=23800.0,
            delta=0.005,
        ))
        assert result.airflow == approx(1000.0, rel_tol=0.03)


# ---------------------------------------------------------------------------
# Total load calculations
# ---------------------------------------------------------------------------

class TestTotalCalc:
    """Total load: Qt = Ct × CFM × Δh."""

    def test_solve_q_total(self):
        result = calculate_airflow(AirflowCalcInput(
            calc_mode=CalcMode.SOLVE_Q,
            load_type=LoadType.TOTAL,
            unit_system=UnitSystem.IP,
            pressure=DEFAULT_PRESSURE_IP,
            airflow=1000.0,
            delta=10.0,   # Δh in BTU/lb
        ))
        # Qt ≈ 4.5 × 1000 × 10 ≈ 45,000 BTU/hr
        assert result.Q == approx(45000.0, rel_tol=0.03)
        assert "Qt" in result.formula

    def test_solve_delta_total(self):
        result = calculate_airflow(AirflowCalcInput(
            calc_mode=CalcMode.SOLVE_DELTA,
            load_type=LoadType.TOTAL,
            unit_system=UnitSystem.IP,
            pressure=DEFAULT_PRESSURE_IP,
            Q=45000.0,
            airflow=1000.0,
        ))
        assert result.delta == approx(10.0, rel_tol=0.03)


# ---------------------------------------------------------------------------
# SI units
# ---------------------------------------------------------------------------

class TestSIUnits:
    """Verify calculations work in SI unit system."""

    def test_sensible_si(self):
        """Qs = ρ × cp × airflow × ΔT in SI."""
        result = calculate_airflow(AirflowCalcInput(
            calc_mode=CalcMode.SOLVE_Q,
            load_type=LoadType.SENSIBLE,
            unit_system=UnitSystem.SI,
            pressure=DEFAULT_PRESSURE_SI,
            airflow=1.0,     # 1 m³/s
            delta=10.0,      # 10°C
            ref_Tdb=21.0,
            ref_W=0.008,
        ))
        # ρ ≈ 1.2 kg/m³, cp = 1006 J/(kg·K)
        # Q ≈ 1.2 × 1006 × 1.0 × 10 ≈ 12,072 W
        assert result.Q == approx(12072.0, rel_tol=0.05)

    def test_c_factor_si_sensible(self):
        C, rho = compute_c_factor(
            LoadType.SENSIBLE, 21.0, 0.008, DEFAULT_PRESSURE_SI, UnitSystem.SI
        )
        # C = ρ × cp, ρ ≈ 1.2, so C ≈ 1207
        assert C == approx(1207.0, rel_tol=0.05)


# ---------------------------------------------------------------------------
# Condensation check
# ---------------------------------------------------------------------------

class TestCondensationCheck:
    """Test condensation detection at surface temperatures."""

    def test_condensing(self):
        """Surface at 50°F, air at 75°F/50% RH (Tdp ≈ 55.3°F) → condensing."""
        result = check_condensation(CondensationCheckInput(
            surface_temp=50.0,
            state_pair=("Tdb", "RH"),
            state_values=(75.0, 50.0),
            unit_system=UnitSystem.IP,
            pressure=DEFAULT_PRESSURE_IP,
        ))
        assert result.is_condensing is True
        assert result.margin < 0
        assert result.dew_point == approx(55.3, abs_tol=1.0)

    def test_not_condensing(self):
        """Surface at 60°F, air at 75°F/50% RH (Tdp ≈ 55.3°F) → not condensing."""
        result = check_condensation(CondensationCheckInput(
            surface_temp=60.0,
            state_pair=("Tdb", "RH"),
            state_values=(75.0, 50.0),
            unit_system=UnitSystem.IP,
            pressure=DEFAULT_PRESSURE_IP,
        ))
        assert result.is_condensing is False
        assert result.margin > 0

    def test_condensation_si(self):
        """SI condensation check: surface 10°C, air 24°C/50% (Tdp ≈ 13°C) → condensing."""
        result = check_condensation(CondensationCheckInput(
            surface_temp=10.0,
            state_pair=("Tdb", "RH"),
            state_values=(24.0, 50.0),
            unit_system=UnitSystem.SI,
            pressure=DEFAULT_PRESSURE_SI,
        ))
        assert result.is_condensing is True


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    """Test error handling and boundary conditions."""

    def test_zero_delta_solve_airflow_raises(self):
        """Cannot solve for airflow when delta is zero."""
        with pytest.raises(ValueError, match="non-zero"):
            calculate_airflow(AirflowCalcInput(
                calc_mode=CalcMode.SOLVE_AIRFLOW,
                load_type=LoadType.SENSIBLE,
                unit_system=UnitSystem.IP,
                pressure=DEFAULT_PRESSURE_IP,
                Q=10000.0,
                delta=0.0,
            ))

    def test_zero_airflow_solve_delta_raises(self):
        """Cannot solve for delta when airflow is zero."""
        with pytest.raises(ValueError, match="positive"):
            calculate_airflow(AirflowCalcInput(
                calc_mode=CalcMode.SOLVE_DELTA,
                load_type=LoadType.SENSIBLE,
                unit_system=UnitSystem.IP,
                pressure=DEFAULT_PRESSURE_IP,
                Q=10000.0,
                airflow=0.0,
            ))

    def test_zero_delta_solve_q_returns_zero(self):
        """Q = C × CFM × 0 = 0."""
        result = calculate_airflow(AirflowCalcInput(
            calc_mode=CalcMode.SOLVE_Q,
            load_type=LoadType.SENSIBLE,
            unit_system=UnitSystem.IP,
            pressure=DEFAULT_PRESSURE_IP,
            airflow=1000.0,
            delta=0.0,
        ))
        assert result.Q == approx(0.0, abs_tol=0.001)

    def test_missing_inputs_raises(self):
        """Missing required inputs should raise ValueError."""
        with pytest.raises(ValueError):
            calculate_airflow(AirflowCalcInput(
                calc_mode=CalcMode.SOLVE_Q,
                load_type=LoadType.SENSIBLE,
                unit_system=UnitSystem.IP,
                pressure=DEFAULT_PRESSURE_IP,
                # Missing airflow and delta
            ))

    def test_custom_reference_conditions(self):
        """Custom ref_Tdb and ref_W should affect C-factor."""
        # Hot, humid conditions → lower density → different C
        result_hot = calculate_airflow(AirflowCalcInput(
            calc_mode=CalcMode.SOLVE_Q,
            load_type=LoadType.SENSIBLE,
            unit_system=UnitSystem.IP,
            pressure=DEFAULT_PRESSURE_IP,
            airflow=1000.0,
            delta=20.0,
            ref_Tdb=100.0,
            ref_W=0.02,
        ))
        result_std = calculate_airflow(AirflowCalcInput(
            calc_mode=CalcMode.SOLVE_Q,
            load_type=LoadType.SENSIBLE,
            unit_system=UnitSystem.IP,
            pressure=DEFAULT_PRESSURE_IP,
            airflow=1000.0,
            delta=20.0,
        ))
        # Hot air is less dense → lower C → lower Q
        assert result_hot.C_factor < result_std.C_factor
        assert result_hot.Q < result_std.Q
