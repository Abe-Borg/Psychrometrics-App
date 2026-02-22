"""
Tests for chemical dehumidification and sensible reheat process solvers.
"""

import pytest

from app.models.process import ProcessInput, ProcessType, DehumidificationMode, SensibleMode
from app.engine.processes.chemical_dehum import ChemicalDehumSolver
from app.engine.processes.sensible import SensibleSolver


# ────────────────────────────────────────────────────────────────────────────
# Chemical Dehumidification — Target W mode
# ────────────────────────────────────────────────────────────────────────────

class TestChemicalDehumTargetW:
    """Chemical dehum: constant enthalpy, target W mode."""

    @pytest.fixture()
    def result(self):
        solver = ChemicalDehumSolver()
        # Start: 80°F / 50% RH → W ≈ 0.011 lb/lb, h ≈ 31 BTU/lb
        inp = ProcessInput(
            process_type=ProcessType.CHEMICAL_DEHUMIDIFICATION,
            unit_system="IP",
            pressure=14.696,
            start_point_pair=("Tdb", "RH"),
            start_point_values=(80.0, 50.0),
            dehum_mode=DehumidificationMode.TARGET_W,
            target_W=0.005,
        )
        return solver.solve(inp)

    def test_w_decreases(self, result):
        assert result.end_point["W"] < result.start_point["W"]

    def test_w_matches_target(self, result):
        assert result.end_point["W"] == pytest.approx(0.005, abs=0.0005)

    def test_tdb_increases(self, result):
        """Desiccant dehumidification raises Tdb (heat of adsorption)."""
        assert result.end_point["Tdb"] > result.start_point["Tdb"]

    def test_enthalpy_approximately_constant(self, result):
        """Enthalpy should stay approximately constant."""
        assert result.end_point["h"] == pytest.approx(
            result.start_point["h"], abs=0.5
        )

    def test_process_type(self, result):
        assert result.process_type == ProcessType.CHEMICAL_DEHUMIDIFICATION

    def test_no_warnings(self, result):
        assert len(result.warnings) == 0

    def test_rh_decreases(self, result):
        """RH should drop significantly (W down, Tdb up)."""
        assert result.end_point["RH"] < result.start_point["RH"]

    def test_metadata(self, result):
        assert "h_constant" in result.metadata
        assert result.metadata["delta_W"] < 0  # dehumidification
        assert result.metadata["delta_Tdb"] > 0  # temperature rises


class TestChemicalDehumTargetRH:
    """Chemical dehum: target RH mode."""

    @pytest.fixture()
    def result(self):
        solver = ChemicalDehumSolver()
        # Start: 80°F / 60% RH → target 20% RH via desiccant
        inp = ProcessInput(
            process_type=ProcessType.CHEMICAL_DEHUMIDIFICATION,
            unit_system="IP",
            pressure=14.696,
            start_point_pair=("Tdb", "RH"),
            start_point_values=(80.0, 60.0),
            dehum_mode=DehumidificationMode.TARGET_RH,
            target_RH=20.0,
        )
        return solver.solve(inp)

    def test_end_rh_matches_target(self, result):
        assert result.end_point["RH"] == pytest.approx(20.0, abs=1.5)

    def test_w_decreases(self, result):
        assert result.end_point["W"] < result.start_point["W"]

    def test_tdb_increases(self, result):
        assert result.end_point["Tdb"] > result.start_point["Tdb"]

    def test_enthalpy_approximately_constant(self, result):
        assert result.end_point["h"] == pytest.approx(
            result.start_point["h"], abs=0.5
        )


class TestChemicalDehumSI:
    """Chemical dehum in SI units."""

    @pytest.fixture()
    def result(self):
        solver = ChemicalDehumSolver()
        # Start: 27°C / 60% RH
        inp = ProcessInput(
            process_type=ProcessType.CHEMICAL_DEHUMIDIFICATION,
            unit_system="SI",
            pressure=101325.0,
            start_point_pair=("Tdb", "RH"),
            start_point_values=(27.0, 60.0),
            dehum_mode=DehumidificationMode.TARGET_W,
            target_W=0.005,
        )
        return solver.solve(inp)

    def test_w_decreases(self, result):
        assert result.end_point["W"] < result.start_point["W"]

    def test_tdb_increases(self, result):
        assert result.end_point["Tdb"] > 27.0

    def test_unit_system(self, result):
        assert result.unit_system == "SI"


class TestChemicalDehumPath:
    """Path follows constant enthalpy line."""

    def test_path_follows_constant_h(self):
        solver = ChemicalDehumSolver()
        inp = ProcessInput(
            process_type=ProcessType.CHEMICAL_DEHUMIDIFICATION,
            unit_system="IP",
            pressure=14.696,
            start_point_pair=("Tdb", "RH"),
            start_point_values=(80.0, 50.0),
            dehum_mode=DehumidificationMode.TARGET_W,
            target_W=0.004,
        )
        result = solver.solve(inp)
        pts = result.path_points
        assert len(pts) >= 10

        # Tdb should increase monotonically as W decreases
        for i in range(1, len(pts)):
            assert pts[i].Tdb >= pts[i - 1].Tdb - 0.01
            assert pts[i].W <= pts[i - 1].W + 1e-7


class TestChemicalDehumEdgeCases:
    """Edge cases for chemical dehumidification."""

    def test_missing_mode(self):
        solver = ChemicalDehumSolver()
        inp = ProcessInput(
            process_type=ProcessType.CHEMICAL_DEHUMIDIFICATION,
            start_point_pair=("Tdb", "RH"),
            start_point_values=(80.0, 50.0),
        )
        with pytest.raises(ValueError, match="dehum_mode"):
            solver.solve(inp)

    def test_missing_target_w(self):
        solver = ChemicalDehumSolver()
        inp = ProcessInput(
            process_type=ProcessType.CHEMICAL_DEHUMIDIFICATION,
            start_point_pair=("Tdb", "RH"),
            start_point_values=(80.0, 50.0),
            dehum_mode=DehumidificationMode.TARGET_W,
        )
        with pytest.raises(ValueError, match="target_W"):
            solver.solve(inp)

    def test_missing_target_rh(self):
        solver = ChemicalDehumSolver()
        inp = ProcessInput(
            process_type=ProcessType.CHEMICAL_DEHUMIDIFICATION,
            start_point_pair=("Tdb", "RH"),
            start_point_values=(80.0, 50.0),
            dehum_mode=DehumidificationMode.TARGET_RH,
        )
        with pytest.raises(ValueError, match="target_RH"):
            solver.solve(inp)

    def test_humidification_warning(self):
        """Target W above start W should produce a warning."""
        solver = ChemicalDehumSolver()
        inp = ProcessInput(
            process_type=ProcessType.CHEMICAL_DEHUMIDIFICATION,
            unit_system="IP",
            pressure=14.696,
            start_point_pair=("Tdb", "RH"),
            start_point_values=(80.0, 20.0),
            dehum_mode=DehumidificationMode.TARGET_W,
            target_W=0.015,
        )
        result = solver.solve(inp)
        assert len(result.warnings) > 0
        assert "humidification" in result.warnings[0].lower()

    def test_small_dehum(self):
        """Very small dehumidification should work without error."""
        solver = ChemicalDehumSolver()
        inp = ProcessInput(
            process_type=ProcessType.CHEMICAL_DEHUMIDIFICATION,
            unit_system="IP",
            pressure=14.696,
            start_point_pair=("Tdb", "RH"),
            start_point_values=(80.0, 50.0),
            dehum_mode=DehumidificationMode.TARGET_W,
            target_W=0.010,  # close to start W
        )
        result = solver.solve(inp)
        assert result.end_point["W"] == pytest.approx(0.010, abs=0.001)


# ────────────────────────────────────────────────────────────────────────────
# Sensible Reheat
# ────────────────────────────────────────────────────────────────────────────

class TestSensibleReheat:
    """Sensible reheat uses the same solver as sensible heating."""

    @pytest.fixture()
    def result(self):
        solver = SensibleSolver()
        # Start: 55°F / 90% RH (typical after cooling coil), reheat to 72°F
        inp = ProcessInput(
            process_type=ProcessType.SENSIBLE_REHEAT,
            unit_system="IP",
            pressure=14.696,
            start_point_pair=("Tdb", "RH"),
            start_point_values=(55.0, 90.0),
            sensible_mode=SensibleMode.TARGET_TDB,
            target_Tdb=72.0,
        )
        return solver.solve(inp)

    def test_tdb_increases(self, result):
        assert result.end_point["Tdb"] == pytest.approx(72.0, abs=0.1)

    def test_w_constant(self, result):
        """Reheat is sensible — W stays constant."""
        assert result.end_point["W"] == pytest.approx(
            result.start_point["W"], abs=0.0001
        )

    def test_process_type_preserved(self, result):
        """Should output SENSIBLE_REHEAT, not SENSIBLE_HEATING."""
        assert result.process_type == ProcessType.SENSIBLE_REHEAT

    def test_rh_decreases(self, result):
        """RH drops when you heat at constant W."""
        assert result.end_point["RH"] < result.start_point["RH"]


class TestSensibleReheatDeltaT:
    """Reheat with delta_t mode."""

    @pytest.fixture()
    def result(self):
        solver = SensibleSolver()
        inp = ProcessInput(
            process_type=ProcessType.SENSIBLE_REHEAT,
            unit_system="IP",
            pressure=14.696,
            start_point_pair=("Tdb", "RH"),
            start_point_values=(55.0, 90.0),
            sensible_mode=SensibleMode.DELTA_T,
            delta_T=15.0,
        )
        return solver.solve(inp)

    def test_tdb_increases_by_15(self, result):
        assert result.end_point["Tdb"] == pytest.approx(70.0, abs=0.1)

    def test_process_type_preserved(self, result):
        assert result.process_type == ProcessType.SENSIBLE_REHEAT


class TestSensibleReheatSI:
    """Reheat in SI units."""

    @pytest.fixture()
    def result(self):
        solver = SensibleSolver()
        inp = ProcessInput(
            process_type=ProcessType.SENSIBLE_REHEAT,
            unit_system="SI",
            pressure=101325.0,
            start_point_pair=("Tdb", "RH"),
            start_point_values=(13.0, 90.0),
            sensible_mode=SensibleMode.TARGET_TDB,
            target_Tdb=22.0,
        )
        return solver.solve(inp)

    def test_tdb_increases(self, result):
        assert result.end_point["Tdb"] == pytest.approx(22.0, abs=0.1)

    def test_unit_system(self, result):
        assert result.unit_system == "SI"

    def test_process_type_preserved(self, result):
        assert result.process_type == ProcessType.SENSIBLE_REHEAT


# ────────────────────────────────────────────────────────────────────────────
# Integration: Desiccant Dehum → Sensible Reheat chain
# ────────────────────────────────────────────────────────────────────────────

class TestDehumReheatChain:
    """Verify a desiccant dehum → sensible reheat sequence makes physical sense."""

    def test_dehum_then_reheat(self):
        # Step 1: Desiccant dehum from 80°F/60% to target W=0.005
        dehum_solver = ChemicalDehumSolver()
        dehum_result = dehum_solver.solve(ProcessInput(
            process_type=ProcessType.CHEMICAL_DEHUMIDIFICATION,
            unit_system="IP",
            pressure=14.696,
            start_point_pair=("Tdb", "RH"),
            start_point_values=(80.0, 60.0),
            dehum_mode=DehumidificationMode.TARGET_W,
            target_W=0.005,
        ))

        # After dehum: Tdb should be higher, W should be 0.005
        assert dehum_result.end_point["Tdb"] > 80.0
        assert dehum_result.end_point["W"] == pytest.approx(0.005, abs=0.001)

        # Step 2: Cool back to 75°F via sensible reheat (actually cooling here)
        reheat_solver = SensibleSolver()
        reheat_result = reheat_solver.solve(ProcessInput(
            process_type=ProcessType.SENSIBLE_REHEAT,
            unit_system="IP",
            pressure=14.696,
            start_point_pair=("Tdb", "W"),
            start_point_values=(
                dehum_result.end_point["Tdb"],
                dehum_result.end_point["W"],
            ),
            sensible_mode=SensibleMode.TARGET_TDB,
            target_Tdb=75.0,
        ))

        # After reheat/cooling: Tdb=75°F, W should still be 0.005
        assert reheat_result.end_point["Tdb"] == pytest.approx(75.0, abs=0.1)
        assert reheat_result.end_point["W"] == pytest.approx(0.005, abs=0.001)

        # The final RH should be much lower than the original 60%
        assert reheat_result.end_point["RH"] < 40.0
