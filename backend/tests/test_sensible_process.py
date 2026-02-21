"""
Tests for the sensible heating/cooling process solver.

Covers all three input modes (TARGET_TDB, DELTA_T, HEAT_AND_AIRFLOW),
edge cases (dew point crossing), both unit systems, and validates
that the process produces correct end states and metadata.
"""

import pytest
from app.config import UnitSystem, DEFAULT_PRESSURE_IP, DEFAULT_PRESSURE_SI
from app.engine.processes.sensible import SensibleSolver
from app.models.process import ProcessInput, ProcessType, SensibleMode


def approx(value: float, rel_tol: float = 0.01, abs_tol: float = 0.1):
    return pytest.approx(value, rel=rel_tol, abs=abs_tol)


@pytest.fixture
def solver():
    return SensibleSolver()


# ---------------------------------------------------------------------------
# Sensible Heating — TARGET_TDB mode
# ---------------------------------------------------------------------------

class TestSensibleHeatingTargetTdb:
    """Heat from 55°F to 75°F at 50% RH initial."""

    def setup_method(self):
        solver = SensibleSolver()
        self.result = solver.solve(ProcessInput(
            process_type=ProcessType.SENSIBLE_HEATING,
            unit_system=UnitSystem.IP,
            pressure=DEFAULT_PRESSURE_IP,
            start_point_pair=("Tdb", "RH"),
            start_point_values=(55.0, 50.0),
            sensible_mode=SensibleMode.TARGET_TDB,
            target_Tdb=75.0,
        ))

    def test_end_tdb(self):
        assert self.result.end_point["Tdb"] == approx(75.0)

    def test_constant_w(self):
        """Humidity ratio must remain constant during sensible process."""
        assert self.result.end_point["W"] == approx(
            self.result.start_point["W"], rel_tol=0.001, abs_tol=1e-6
        )

    def test_start_tdb(self):
        assert self.result.start_point["Tdb"] == approx(55.0)

    def test_process_type_is_heating(self):
        assert self.result.process_type == ProcessType.SENSIBLE_HEATING

    def test_delta_t_metadata(self):
        assert self.result.metadata["delta_T"] == approx(20.0)

    def test_rh_decreased(self):
        """RH should decrease when heating at constant W."""
        assert self.result.end_point["RH"] < self.result.start_point["RH"]

    def test_path_has_two_points(self):
        assert len(self.result.path_points) == 2

    def test_path_is_horizontal(self):
        """Both path points should have the same W."""
        assert self.result.path_points[0].W == self.result.path_points[1].W

    def test_no_warnings(self):
        assert len(self.result.warnings) == 0


# ---------------------------------------------------------------------------
# Sensible Cooling — TARGET_TDB mode
# ---------------------------------------------------------------------------

class TestSensibleCoolingTargetTdb:
    """Cool from 75°F to 55°F at 50% RH initial."""

    def setup_method(self):
        solver = SensibleSolver()
        self.result = solver.solve(ProcessInput(
            process_type=ProcessType.SENSIBLE_COOLING,
            unit_system=UnitSystem.IP,
            pressure=DEFAULT_PRESSURE_IP,
            start_point_pair=("Tdb", "RH"),
            start_point_values=(75.0, 50.0),
            sensible_mode=SensibleMode.TARGET_TDB,
            target_Tdb=55.0,
        ))

    def test_end_tdb(self):
        assert self.result.end_point["Tdb"] == approx(55.0)

    def test_constant_w(self):
        assert self.result.end_point["W"] == approx(
            self.result.start_point["W"], rel_tol=0.001, abs_tol=1e-6
        )

    def test_process_type_is_cooling(self):
        assert self.result.process_type == ProcessType.SENSIBLE_COOLING

    def test_delta_t_is_negative(self):
        assert self.result.metadata["delta_T"] == approx(-20.0)

    def test_rh_increased(self):
        """RH should increase when cooling at constant W."""
        assert self.result.end_point["RH"] > self.result.start_point["RH"]


# ---------------------------------------------------------------------------
# Sensible Heating/Cooling symmetry
# ---------------------------------------------------------------------------

class TestSensibleSymmetry:
    """Heating and cooling between the same two states should be symmetric."""

    def setup_method(self):
        solver = SensibleSolver()
        self.heat = solver.solve(ProcessInput(
            process_type=ProcessType.SENSIBLE_HEATING,
            unit_system=UnitSystem.IP,
            pressure=DEFAULT_PRESSURE_IP,
            start_point_pair=("Tdb", "RH"),
            start_point_values=(55.0, 50.0),
            sensible_mode=SensibleMode.TARGET_TDB,
            target_Tdb=75.0,
        ))
        self.cool = solver.solve(ProcessInput(
            process_type=ProcessType.SENSIBLE_COOLING,
            unit_system=UnitSystem.IP,
            pressure=DEFAULT_PRESSURE_IP,
            start_point_pair=("Tdb", "RH"),
            start_point_values=(75.0, 50.0),
            sensible_mode=SensibleMode.TARGET_TDB,
            target_Tdb=55.0,
        ))

    def test_qs_magnitude_matches(self):
        """Sensible energy should be equal in magnitude for heat and cool."""
        q_heat = abs(self.heat.metadata["Qs_per_unit_mass"])
        q_cool = abs(self.cool.metadata["Qs_per_unit_mass"])
        assert q_heat == approx(q_cool, rel_tol=0.02, abs_tol=0.1)


# ---------------------------------------------------------------------------
# DELTA_T mode
# ---------------------------------------------------------------------------

class TestDeltaTMode:
    """Test DELTA_T input mode."""

    def setup_method(self):
        solver = SensibleSolver()
        self.result = solver.solve(ProcessInput(
            process_type=ProcessType.SENSIBLE_HEATING,
            unit_system=UnitSystem.IP,
            pressure=DEFAULT_PRESSURE_IP,
            start_point_pair=("Tdb", "RH"),
            start_point_values=(55.0, 50.0),
            sensible_mode=SensibleMode.DELTA_T,
            delta_T=20.0,
        ))

    def test_end_tdb(self):
        assert self.result.end_point["Tdb"] == approx(75.0)

    def test_constant_w(self):
        assert self.result.end_point["W"] == approx(
            self.result.start_point["W"], rel_tol=0.001, abs_tol=1e-6
        )


class TestDeltaTNegative:
    """Negative delta_T should result in cooling."""

    def setup_method(self):
        solver = SensibleSolver()
        self.result = solver.solve(ProcessInput(
            process_type=ProcessType.SENSIBLE_COOLING,
            unit_system=UnitSystem.IP,
            pressure=DEFAULT_PRESSURE_IP,
            start_point_pair=("Tdb", "RH"),
            start_point_values=(75.0, 50.0),
            sensible_mode=SensibleMode.DELTA_T,
            delta_T=-20.0,
        ))

    def test_end_tdb(self):
        assert self.result.end_point["Tdb"] == approx(55.0)

    def test_process_type_is_cooling(self):
        assert self.result.process_type == ProcessType.SENSIBLE_COOLING


# ---------------------------------------------------------------------------
# HEAT_AND_AIRFLOW mode
# ---------------------------------------------------------------------------

class TestHeatAndAirflowMode:
    """
    Test HEAT_AND_AIRFLOW mode.
    At sea level: C ≈ 1.08 BTU/(hr·CFM·°F)
    Q = 1.08 × 1000 CFM × 20°F = 21,600 BTU/hr
    So given Q=21600 and CFM=1000, we expect ΔT ≈ 20°F.
    """

    def setup_method(self):
        solver = SensibleSolver()
        self.result = solver.solve(ProcessInput(
            process_type=ProcessType.SENSIBLE_HEATING,
            unit_system=UnitSystem.IP,
            pressure=DEFAULT_PRESSURE_IP,
            start_point_pair=("Tdb", "RH"),
            start_point_values=(55.0, 50.0),
            sensible_mode=SensibleMode.HEAT_AND_AIRFLOW,
            Q_sensible=21600.0,
            airflow_cfm=1000.0,
        ))

    def test_delta_t_approximately_20(self):
        """ΔT should be approximately 20°F (C factor is ~1.08 at sea level)."""
        delta_T = self.result.metadata["delta_T"]
        assert 18.0 <= delta_T <= 22.0

    def test_end_tdb(self):
        """End Tdb should be roughly 55 + 20 = 75°F."""
        assert 73.0 <= self.result.end_point["Tdb"] <= 77.0

    def test_c_factor_near_one_point_zero_eight(self):
        """At sea level, C factor should be approximately 1.08-1.12 (varies with conditions)."""
        assert 1.05 <= self.result.metadata["C_factor"] <= 1.15

    def test_metadata_has_airflow(self):
        assert self.result.metadata["airflow"] == 1000.0


# ---------------------------------------------------------------------------
# Edge case: Cooling below dew point
# ---------------------------------------------------------------------------

class TestCoolingBelowDewPoint:
    """Cooling from 75°F/50% RH to 40°F — below the dew point (~55°F)."""

    def setup_method(self):
        solver = SensibleSolver()
        self.result = solver.solve(ProcessInput(
            process_type=ProcessType.SENSIBLE_COOLING,
            unit_system=UnitSystem.IP,
            pressure=DEFAULT_PRESSURE_IP,
            start_point_pair=("Tdb", "RH"),
            start_point_values=(75.0, 50.0),
            sensible_mode=SensibleMode.TARGET_TDB,
            target_Tdb=40.0,
        ))

    def test_warning_issued(self):
        assert len(self.result.warnings) > 0
        assert "dew point" in self.result.warnings[0].lower()

    def test_calculation_still_completes(self):
        """Even with the warning, the calculation should complete."""
        assert self.result.end_point["Tdb"] == approx(40.0)

    def test_w_still_constant(self):
        """W stays constant in the sensible calculation (warning only)."""
        assert self.result.end_point["W"] == approx(
            self.result.start_point["W"], rel_tol=0.001, abs_tol=1e-6
        )


# ---------------------------------------------------------------------------
# SI Units
# ---------------------------------------------------------------------------

class TestSensibleHeatingSI:
    """Sensible heating in SI: 15°C to 25°C at 50% RH."""

    def setup_method(self):
        solver = SensibleSolver()
        self.result = solver.solve(ProcessInput(
            process_type=ProcessType.SENSIBLE_HEATING,
            unit_system=UnitSystem.SI,
            pressure=DEFAULT_PRESSURE_SI,
            start_point_pair=("Tdb", "RH"),
            start_point_values=(15.0, 50.0),
            sensible_mode=SensibleMode.TARGET_TDB,
            target_Tdb=25.0,
        ))

    def test_end_tdb(self):
        assert self.result.end_point["Tdb"] == approx(25.0)

    def test_constant_w(self):
        assert self.result.end_point["W"] == approx(
            self.result.start_point["W"], rel_tol=0.001, abs_tol=1e-6
        )

    def test_delta_t_metadata(self):
        assert self.result.metadata["delta_T"] == approx(10.0)

    def test_unit_system_in_output(self):
        assert self.result.unit_system == UnitSystem.SI


# ---------------------------------------------------------------------------
# Altitude correction
# ---------------------------------------------------------------------------

class TestAltitudeCorrection:
    """At Denver altitude (5280 ft), C factor should be lower than 1.08."""

    def setup_method(self):
        solver = SensibleSolver()
        # Denver pressure ≈ 12.23 psia
        from app.engine.state_resolver import get_pressure_from_altitude
        self.denver_pressure = get_pressure_from_altitude(5280.0, UnitSystem.IP)
        self.result = solver.solve(ProcessInput(
            process_type=ProcessType.SENSIBLE_HEATING,
            unit_system=UnitSystem.IP,
            pressure=self.denver_pressure,
            start_point_pair=("Tdb", "RH"),
            start_point_values=(55.0, 50.0),
            sensible_mode=SensibleMode.HEAT_AND_AIRFLOW,
            Q_sensible=21600.0,
            airflow_cfm=1000.0,
        ))

    def test_c_factor_lower_at_altitude(self):
        """C factor at altitude should be less than sea-level 1.08."""
        assert self.result.metadata["C_factor"] < 1.05

    def test_delta_t_larger_at_altitude(self):
        """Same Q and CFM at altitude → larger ΔT (thinner air)."""
        assert self.result.metadata["delta_T"] > 20.5


# ---------------------------------------------------------------------------
# Validation errors
# ---------------------------------------------------------------------------

class TestValidationErrors:

    def test_missing_sensible_mode(self):
        solver = SensibleSolver()
        with pytest.raises(ValueError, match="sensible_mode is required"):
            solver.solve(ProcessInput(
                process_type=ProcessType.SENSIBLE_HEATING,
                start_point_pair=("Tdb", "RH"),
                start_point_values=(55.0, 50.0),
            ))

    def test_missing_target_tdb(self):
        solver = SensibleSolver()
        with pytest.raises(ValueError, match="target_Tdb is required"):
            solver.solve(ProcessInput(
                process_type=ProcessType.SENSIBLE_HEATING,
                start_point_pair=("Tdb", "RH"),
                start_point_values=(55.0, 50.0),
                sensible_mode=SensibleMode.TARGET_TDB,
            ))

    def test_missing_delta_t(self):
        solver = SensibleSolver()
        with pytest.raises(ValueError, match="delta_T is required"):
            solver.solve(ProcessInput(
                process_type=ProcessType.SENSIBLE_HEATING,
                start_point_pair=("Tdb", "RH"),
                start_point_values=(55.0, 50.0),
                sensible_mode=SensibleMode.DELTA_T,
            ))

    def test_missing_q_and_cfm(self):
        solver = SensibleSolver()
        with pytest.raises(ValueError, match="Q_sensible and airflow_cfm"):
            solver.solve(ProcessInput(
                process_type=ProcessType.SENSIBLE_HEATING,
                start_point_pair=("Tdb", "RH"),
                start_point_values=(55.0, 50.0),
                sensible_mode=SensibleMode.HEAT_AND_AIRFLOW,
            ))

    def test_zero_airflow(self):
        solver = SensibleSolver()
        with pytest.raises(ValueError, match="airflow_cfm must be positive"):
            solver.solve(ProcessInput(
                process_type=ProcessType.SENSIBLE_HEATING,
                start_point_pair=("Tdb", "RH"),
                start_point_values=(55.0, 50.0),
                sensible_mode=SensibleMode.HEAT_AND_AIRFLOW,
                Q_sensible=21600.0,
                airflow_cfm=0.0,
            ))
