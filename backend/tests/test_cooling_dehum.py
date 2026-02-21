"""
Tests for the cooling & dehumidification process solver.

Covers forward mode (ADP + BF → leaving), reverse mode (entering + leaving → ADP + BF),
round-trip consistency, load calculations, edge cases, and SI units.
"""

import pytest
from app.config import UnitSystem, DEFAULT_PRESSURE_IP, DEFAULT_PRESSURE_SI
from app.engine.processes.cooling_dehum import CoolingDehumSolver
from app.models.process import ProcessInput, ProcessType, CoolingDehumMode


def approx(value: float, rel_tol: float = 0.01, abs_tol: float = 0.1):
    return pytest.approx(value, rel=rel_tol, abs=abs_tol)


@pytest.fixture
def solver():
    return CoolingDehumSolver()


# ---------------------------------------------------------------------------
# Forward mode: ADP + BF → leaving state
# ---------------------------------------------------------------------------

class TestForwardMode:
    """
    Forward mode test using a known ADP and BF.
    Entering: 80°F, 67°F wb (typical summer design condition).
    ADP: 45°F (saturated), BF: 0.15
    """

    def setup_method(self):
        solver = CoolingDehumSolver()
        self.result = solver.solve(ProcessInput(
            process_type=ProcessType.COOLING_DEHUMIDIFICATION,
            unit_system=UnitSystem.IP,
            pressure=DEFAULT_PRESSURE_IP,
            start_point_pair=("Tdb", "Twb"),
            start_point_values=(80.0, 67.0),
            cooling_dehum_mode=CoolingDehumMode.FORWARD,
            adp_Tdb=45.0,
            bypass_factor=0.15,
        ))

    def test_leaving_tdb(self):
        """Leaving Tdb = ADP + BF × (entering - ADP) = 45 + 0.15 × (80-45) = 50.25°F"""
        assert self.result.end_point["Tdb"] == approx(50.25, abs_tol=0.5)

    def test_leaving_w_lower_than_entering(self):
        """Leaving W must be lower than entering W (dehumidification occurred)."""
        assert self.result.end_point["W"] < self.result.start_point["W"]

    def test_leaving_rh_high(self):
        """Leaving air off a cooling coil should have high RH (typically 85-95%)."""
        assert self.result.end_point["RH"] > 80.0

    def test_process_type(self):
        assert self.result.process_type == ProcessType.COOLING_DEHUMIDIFICATION

    def test_metadata_has_adp(self):
        assert self.result.metadata["ADP_Tdb"] == approx(45.0)

    def test_metadata_has_bf(self):
        assert self.result.metadata["BF"] == approx(0.15)

    def test_metadata_has_cf(self):
        assert self.result.metadata["CF"] == approx(0.85)

    def test_metadata_has_shr(self):
        """SHR should be between 0 and 1 for a cooling/dehum process."""
        assert 0.0 < self.result.metadata["SHR"] < 1.0

    def test_qt_positive(self):
        """Total heat should be positive (heat removed from air)."""
        assert self.result.metadata["Qt"] > 0

    def test_qs_positive(self):
        assert self.result.metadata["Qs"] > 0

    def test_ql_positive(self):
        assert self.result.metadata["Ql"] > 0

    def test_qt_equals_qs_plus_ql(self):
        Qt = self.result.metadata["Qt"]
        Qs = self.result.metadata["Qs"]
        Ql = self.result.metadata["Ql"]
        assert Qt == approx(Qs + Ql, rel_tol=0.01, abs_tol=0.05)

    def test_path_has_intermediate_points(self):
        """Path should have more than just start and end."""
        assert len(self.result.path_points) >= 3

    def test_no_warnings(self):
        assert len(self.result.warnings) == 0


# ---------------------------------------------------------------------------
# Reverse mode: entering + leaving → ADP + BF
# ---------------------------------------------------------------------------

class TestReverseMode:
    """
    Reverse mode test: classic textbook problem.
    Entering: 80°F db, 67°F wb
    Leaving: 55°F db, 90% RH (approximately 54°F wb)
    """

    def setup_method(self):
        solver = CoolingDehumSolver()
        self.result = solver.solve(ProcessInput(
            process_type=ProcessType.COOLING_DEHUMIDIFICATION,
            unit_system=UnitSystem.IP,
            pressure=DEFAULT_PRESSURE_IP,
            start_point_pair=("Tdb", "Twb"),
            start_point_values=(80.0, 67.0),
            cooling_dehum_mode=CoolingDehumMode.REVERSE,
            leaving_Tdb=55.0,
            leaving_RH=90.0,
        ))

    def test_adp_tdb_reasonable(self):
        """ADP should be below the leaving Tdb."""
        assert self.result.metadata["ADP_Tdb"] < 55.0

    def test_adp_tdb_in_range(self):
        """ADP should be a reasonable coil temperature (30-55°F typically)."""
        assert 30.0 <= self.result.metadata["ADP_Tdb"] <= 55.0

    def test_bf_in_range(self):
        """BF should be between 0 and 1."""
        assert 0.0 < self.result.metadata["BF"] < 1.0

    def test_bf_reasonable(self):
        """Typical coil BF is 0.05-0.25."""
        assert 0.01 <= self.result.metadata["BF"] <= 0.40

    def test_shr_in_range(self):
        assert 0.0 < self.result.metadata["SHR"] < 1.0

    def test_leaving_tdb(self):
        assert self.result.end_point["Tdb"] == approx(55.0)

    def test_leaving_rh(self):
        assert self.result.end_point["RH"] == approx(90.0)


# ---------------------------------------------------------------------------
# Round-trip consistency: forward then reverse should match
# ---------------------------------------------------------------------------

class TestRoundTrip:
    """
    Forward mode produces a leaving state. Using that leaving state in
    reverse mode should recover the same ADP and BF.
    """

    def setup_method(self):
        solver = CoolingDehumSolver()

        # Forward: get leaving state from known ADP + BF
        self.forward = solver.solve(ProcessInput(
            process_type=ProcessType.COOLING_DEHUMIDIFICATION,
            unit_system=UnitSystem.IP,
            pressure=DEFAULT_PRESSURE_IP,
            start_point_pair=("Tdb", "Twb"),
            start_point_values=(80.0, 67.0),
            cooling_dehum_mode=CoolingDehumMode.FORWARD,
            adp_Tdb=45.0,
            bypass_factor=0.15,
        ))

        # Reverse: use the leaving state from forward to recover ADP + BF
        leaving_Tdb = self.forward.end_point["Tdb"]
        leaving_RH = self.forward.end_point["RH"]

        self.reverse = solver.solve(ProcessInput(
            process_type=ProcessType.COOLING_DEHUMIDIFICATION,
            unit_system=UnitSystem.IP,
            pressure=DEFAULT_PRESSURE_IP,
            start_point_pair=("Tdb", "Twb"),
            start_point_values=(80.0, 67.0),
            cooling_dehum_mode=CoolingDehumMode.REVERSE,
            leaving_Tdb=leaving_Tdb,
            leaving_RH=leaving_RH,
        ))

    def test_adp_matches(self):
        """Reverse mode should recover the same ADP as forward mode."""
        assert self.reverse.metadata["ADP_Tdb"] == approx(
            self.forward.metadata["ADP_Tdb"], rel_tol=0.01, abs_tol=0.5
        )

    def test_bf_matches(self):
        """Reverse mode should recover the same BF as forward mode."""
        assert self.reverse.metadata["BF"] == approx(
            self.forward.metadata["BF"], rel_tol=0.02, abs_tol=0.01
        )

    def test_shr_matches(self):
        assert self.reverse.metadata["SHR"] == approx(
            self.forward.metadata["SHR"], rel_tol=0.02, abs_tol=0.02
        )


# ---------------------------------------------------------------------------
# Different BF values
# ---------------------------------------------------------------------------

class TestVaryingBypassFactors:
    """Lower BF → leaving state closer to ADP; higher BF → closer to entering."""

    def setup_method(self):
        solver = CoolingDehumSolver()
        base = dict(
            process_type=ProcessType.COOLING_DEHUMIDIFICATION,
            unit_system=UnitSystem.IP,
            pressure=DEFAULT_PRESSURE_IP,
            start_point_pair=("Tdb", "Twb"),
            start_point_values=(80.0, 67.0),
            cooling_dehum_mode=CoolingDehumMode.FORWARD,
            adp_Tdb=45.0,
        )
        self.low_bf = solver.solve(ProcessInput(**base, bypass_factor=0.05))
        self.high_bf = solver.solve(ProcessInput(**base, bypass_factor=0.30))

    def test_lower_bf_means_lower_leaving_tdb(self):
        assert self.low_bf.end_point["Tdb"] < self.high_bf.end_point["Tdb"]

    def test_lower_bf_means_lower_leaving_w(self):
        assert self.low_bf.end_point["W"] < self.high_bf.end_point["W"]

    def test_lower_bf_means_higher_qt(self):
        """More cooling occurs with lower BF (more contact with coil)."""
        assert self.low_bf.metadata["Qt"] > self.high_bf.metadata["Qt"]


# ---------------------------------------------------------------------------
# SI Units
# ---------------------------------------------------------------------------

class TestCoolingDehumSI:
    """Cooling & dehumidification in SI units."""

    def setup_method(self):
        solver = CoolingDehumSolver()
        self.result = solver.solve(ProcessInput(
            process_type=ProcessType.COOLING_DEHUMIDIFICATION,
            unit_system=UnitSystem.SI,
            pressure=DEFAULT_PRESSURE_SI,
            start_point_pair=("Tdb", "Twb"),
            start_point_values=(27.0, 20.0),  # ~80°F/68°F wb equivalent
            cooling_dehum_mode=CoolingDehumMode.FORWARD,
            adp_Tdb=7.0,  # ~45°F equivalent
            bypass_factor=0.15,
        ))

    def test_leaving_tdb(self):
        """Leaving = 7 + 0.15 × (27-7) = 10.0°C"""
        assert self.result.end_point["Tdb"] == approx(10.0, abs_tol=0.5)

    def test_unit_system(self):
        assert self.result.unit_system == UnitSystem.SI

    def test_w_decreased(self):
        assert self.result.end_point["W"] < self.result.start_point["W"]

    def test_qt_positive(self):
        assert self.result.metadata["Qt"] > 0


# ---------------------------------------------------------------------------
# Edge cases and validation errors
# ---------------------------------------------------------------------------

class TestEdgeCases:

    def test_missing_mode(self):
        solver = CoolingDehumSolver()
        with pytest.raises(ValueError, match="cooling_dehum_mode is required"):
            solver.solve(ProcessInput(
                process_type=ProcessType.COOLING_DEHUMIDIFICATION,
                start_point_pair=("Tdb", "RH"),
                start_point_values=(80.0, 50.0),
            ))

    def test_forward_missing_adp(self):
        solver = CoolingDehumSolver()
        with pytest.raises(ValueError, match="adp_Tdb and bypass_factor"):
            solver.solve(ProcessInput(
                process_type=ProcessType.COOLING_DEHUMIDIFICATION,
                start_point_pair=("Tdb", "RH"),
                start_point_values=(80.0, 50.0),
                cooling_dehum_mode=CoolingDehumMode.FORWARD,
            ))

    def test_forward_bf_out_of_range(self):
        solver = CoolingDehumSolver()
        with pytest.raises(ValueError, match="bypass_factor must be between"):
            solver.solve(ProcessInput(
                process_type=ProcessType.COOLING_DEHUMIDIFICATION,
                start_point_pair=("Tdb", "RH"),
                start_point_values=(80.0, 50.0),
                cooling_dehum_mode=CoolingDehumMode.FORWARD,
                adp_Tdb=45.0,
                bypass_factor=1.5,
            ))

    def test_reverse_missing_leaving(self):
        solver = CoolingDehumSolver()
        with pytest.raises(ValueError, match="leaving_Tdb and leaving_RH"):
            solver.solve(ProcessInput(
                process_type=ProcessType.COOLING_DEHUMIDIFICATION,
                start_point_pair=("Tdb", "RH"),
                start_point_values=(80.0, 50.0),
                cooling_dehum_mode=CoolingDehumMode.REVERSE,
            ))

    def test_reverse_leaving_tdb_higher_than_entering(self):
        solver = CoolingDehumSolver()
        with pytest.raises(ValueError, match="Leaving Tdb.*must be less than entering"):
            solver.solve(ProcessInput(
                process_type=ProcessType.COOLING_DEHUMIDIFICATION,
                start_point_pair=("Tdb", "RH"),
                start_point_values=(80.0, 50.0),
                cooling_dehum_mode=CoolingDehumMode.REVERSE,
                leaving_Tdb=85.0,
                leaving_RH=90.0,
            ))

    def test_adp_above_dew_point_warns(self):
        """ADP above entering dew point should produce a warning."""
        solver = CoolingDehumSolver()
        # 80°F/50% RH has dew point ~59°F; ADP at 65°F is above it
        result = solver.solve(ProcessInput(
            process_type=ProcessType.COOLING_DEHUMIDIFICATION,
            start_point_pair=("Tdb", "RH"),
            start_point_values=(80.0, 50.0),
            cooling_dehum_mode=CoolingDehumMode.FORWARD,
            adp_Tdb=65.0,
            bypass_factor=0.15,
        ))
        assert len(result.warnings) > 0
        assert "dew point" in result.warnings[0].lower()
