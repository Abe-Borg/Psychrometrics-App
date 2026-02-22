"""
Tests for evaporative cooling process solvers: direct, indirect, two-stage.
"""

import pytest

from app.models.process import ProcessInput, ProcessType
from app.engine.processes.evaporative import (
    DirectEvaporativeSolver,
    IndirectEvaporativeSolver,
    IndirectDirectEvaporativeSolver,
)


# ────────────────────────────────────────────────────────────────────────────
# Direct Evaporative Cooling
# ────────────────────────────────────────────────────────────────────────────

class TestDirectEvaporative:
    """Direct evaporative cooling at 80% effectiveness."""

    @pytest.fixture()
    def result(self):
        solver = DirectEvaporativeSolver()
        inp = ProcessInput(
            process_type=ProcessType.DIRECT_EVAPORATIVE,
            unit_system="IP",
            pressure=14.696,
            start_point_pair=("Tdb", "RH"),
            start_point_values=(95.0, 20.0),
            effectiveness=0.8,
        )
        return solver.solve(inp)

    def test_tdb_decreases(self, result):
        assert result.end_point["Tdb"] < result.start_point["Tdb"]

    def test_w_increases(self, result):
        assert result.end_point["W"] > result.start_point["W"]

    def test_twb_constant(self, result):
        """Wet-bulb should remain approximately constant."""
        assert result.end_point["Twb"] == pytest.approx(
            result.start_point["Twb"], abs=0.5
        )

    def test_effectiveness_formula(self, result):
        """Verify ε = (Tdb_in - Tdb_out) / (Tdb_in - Twb_in)."""
        Tdb_in = result.start_point["Tdb"]
        Tdb_out = result.end_point["Tdb"]
        Twb = result.start_point["Twb"]
        computed_eff = (Tdb_in - Tdb_out) / (Tdb_in - Twb)
        assert computed_eff == pytest.approx(0.8, abs=0.01)

    def test_rh_increases(self, result):
        assert result.end_point["RH"] > result.start_point["RH"]

    def test_process_type(self, result):
        assert result.process_type == ProcessType.DIRECT_EVAPORATIVE

    def test_no_warnings(self, result):
        assert len(result.warnings) == 0

    def test_metadata(self, result):
        assert result.metadata["effectiveness"] == pytest.approx(0.8, abs=0.01)
        assert result.metadata["delta_Tdb"] < 0  # cooling


class TestDirectEvaporative100Pct:
    """DEC at 100% effectiveness → saturation."""

    @pytest.fixture()
    def result(self):
        solver = DirectEvaporativeSolver()
        inp = ProcessInput(
            process_type=ProcessType.DIRECT_EVAPORATIVE,
            unit_system="IP",
            pressure=14.696,
            start_point_pair=("Tdb", "RH"),
            start_point_values=(95.0, 20.0),
            effectiveness=1.0,
        )
        return solver.solve(inp)

    def test_end_rh_100(self, result):
        assert result.end_point["RH"] == pytest.approx(100.0, abs=1.0)

    def test_end_tdb_equals_twb(self, result):
        assert result.end_point["Tdb"] == pytest.approx(
            result.start_point["Twb"], abs=0.5
        )


class TestDirectEvaporativeSI:
    """DEC in SI units."""

    @pytest.fixture()
    def result(self):
        solver = DirectEvaporativeSolver()
        inp = ProcessInput(
            process_type=ProcessType.DIRECT_EVAPORATIVE,
            unit_system="SI",
            pressure=101325.0,
            start_point_pair=("Tdb", "RH"),
            start_point_values=(35.0, 20.0),
            effectiveness=0.85,
        )
        return solver.solve(inp)

    def test_tdb_decreases(self, result):
        assert result.end_point["Tdb"] < 35.0

    def test_unit_system(self, result):
        assert result.unit_system == "SI"


class TestDirectEvaporativeEdgeCases:
    """Edge cases for DEC."""

    def test_missing_effectiveness(self):
        solver = DirectEvaporativeSolver()
        inp = ProcessInput(
            process_type=ProcessType.DIRECT_EVAPORATIVE,
            start_point_pair=("Tdb", "RH"),
            start_point_values=(95.0, 20.0),
        )
        with pytest.raises(ValueError, match="effectiveness"):
            solver.solve(inp)

    def test_effectiveness_out_of_range(self):
        solver = DirectEvaporativeSolver()
        inp = ProcessInput(
            process_type=ProcessType.DIRECT_EVAPORATIVE,
            start_point_pair=("Tdb", "RH"),
            start_point_values=(95.0, 20.0),
            effectiveness=1.5,
        )
        with pytest.raises(ValueError, match="between 0 and 1"):
            solver.solve(inp)

    def test_zero_effectiveness(self):
        solver = DirectEvaporativeSolver()
        inp = ProcessInput(
            process_type=ProcessType.DIRECT_EVAPORATIVE,
            unit_system="IP",
            pressure=14.696,
            start_point_pair=("Tdb", "RH"),
            start_point_values=(95.0, 20.0),
            effectiveness=0.0,
        )
        result = solver.solve(inp)
        assert result.end_point["Tdb"] == pytest.approx(95.0, abs=0.1)

    def test_path_has_many_points(self):
        solver = DirectEvaporativeSolver()
        inp = ProcessInput(
            process_type=ProcessType.DIRECT_EVAPORATIVE,
            unit_system="IP",
            pressure=14.696,
            start_point_pair=("Tdb", "RH"),
            start_point_values=(95.0, 20.0),
            effectiveness=0.8,
        )
        result = solver.solve(inp)
        assert len(result.path_points) >= 10


# ────────────────────────────────────────────────────────────────────────────
# Indirect Evaporative Cooling
# ────────────────────────────────────────────────────────────────────────────

class TestIndirectEvaporative:
    """IEC with default secondary air (same as primary)."""

    @pytest.fixture()
    def result(self):
        solver = IndirectEvaporativeSolver()
        inp = ProcessInput(
            process_type=ProcessType.INDIRECT_EVAPORATIVE,
            unit_system="IP",
            pressure=14.696,
            start_point_pair=("Tdb", "RH"),
            start_point_values=(95.0, 20.0),
            effectiveness=0.7,
        )
        return solver.solve(inp)

    def test_tdb_decreases(self, result):
        assert result.end_point["Tdb"] < result.start_point["Tdb"]

    def test_w_constant(self, result):
        """Indirect evap is sensible cooling — W stays constant."""
        assert result.end_point["W"] == pytest.approx(
            result.start_point["W"], abs=0.0001
        )

    def test_rh_increases(self, result):
        """RH increases because Tdb drops while W stays constant."""
        assert result.end_point["RH"] > result.start_point["RH"]

    def test_process_type(self, result):
        assert result.process_type == ProcessType.INDIRECT_EVAPORATIVE

    def test_effectiveness_formula(self, result):
        """ε = (Tdb_in - Tdb_out) / (Tdb_in - Twb_secondary)."""
        Tdb_in = result.start_point["Tdb"]
        Tdb_out = result.end_point["Tdb"]
        Twb_sec = result.metadata["secondary_Twb"]
        computed_eff = (Tdb_in - Tdb_out) / (Tdb_in - Twb_sec)
        assert computed_eff == pytest.approx(0.7, abs=0.01)

    def test_no_warnings(self, result):
        assert len(result.warnings) == 0


class TestIndirectEvaporativeWithSecondary:
    """IEC with a different secondary airstream."""

    @pytest.fixture()
    def result(self):
        solver = IndirectEvaporativeSolver()
        # Primary: 95°F/20% RH. Secondary: 85°F/50% RH (lower Twb)
        inp = ProcessInput(
            process_type=ProcessType.INDIRECT_EVAPORATIVE,
            unit_system="IP",
            pressure=14.696,
            start_point_pair=("Tdb", "RH"),
            start_point_values=(95.0, 20.0),
            effectiveness=0.7,
            secondary_air_pair=("Tdb", "RH"),
            secondary_air_values=(85.0, 50.0),
        )
        return solver.solve(inp)

    def test_tdb_decreases(self, result):
        assert result.end_point["Tdb"] < 95.0

    def test_w_constant(self, result):
        assert result.end_point["W"] == pytest.approx(
            result.start_point["W"], abs=0.0001
        )

    def test_secondary_twb_used(self, result):
        """The secondary Twb should be different from the primary."""
        assert result.metadata["secondary_Twb"] != pytest.approx(
            result.start_point["Twb"], abs=1.0
        )

    def test_effectiveness_formula(self, result):
        Tdb_in = result.start_point["Tdb"]
        Tdb_out = result.end_point["Tdb"]
        Twb_sec = result.metadata["secondary_Twb"]
        computed_eff = (Tdb_in - Tdb_out) / (Tdb_in - Twb_sec)
        assert computed_eff == pytest.approx(0.7, abs=0.01)


class TestIndirectEvaporativeSI:
    """IEC in SI units."""

    @pytest.fixture()
    def result(self):
        solver = IndirectEvaporativeSolver()
        inp = ProcessInput(
            process_type=ProcessType.INDIRECT_EVAPORATIVE,
            unit_system="SI",
            pressure=101325.0,
            start_point_pair=("Tdb", "RH"),
            start_point_values=(35.0, 20.0),
            effectiveness=0.7,
        )
        return solver.solve(inp)

    def test_tdb_decreases(self, result):
        assert result.end_point["Tdb"] < 35.0

    def test_w_constant(self, result):
        assert result.end_point["W"] == pytest.approx(
            result.start_point["W"], abs=0.0001
        )

    def test_unit_system(self, result):
        assert result.unit_system == "SI"


class TestIndirectEvaporativeEdgeCases:
    """Edge cases for IEC."""

    def test_missing_effectiveness(self):
        solver = IndirectEvaporativeSolver()
        inp = ProcessInput(
            process_type=ProcessType.INDIRECT_EVAPORATIVE,
            start_point_pair=("Tdb", "RH"),
            start_point_values=(95.0, 20.0),
        )
        with pytest.raises(ValueError, match="effectiveness"):
            solver.solve(inp)

    def test_effectiveness_out_of_range(self):
        solver = IndirectEvaporativeSolver()
        inp = ProcessInput(
            process_type=ProcessType.INDIRECT_EVAPORATIVE,
            start_point_pair=("Tdb", "RH"),
            start_point_values=(95.0, 20.0),
            effectiveness=-0.1,
        )
        with pytest.raises(ValueError, match="between 0 and 1"):
            solver.solve(inp)

    def test_zero_effectiveness(self):
        solver = IndirectEvaporativeSolver()
        inp = ProcessInput(
            process_type=ProcessType.INDIRECT_EVAPORATIVE,
            unit_system="IP",
            pressure=14.696,
            start_point_pair=("Tdb", "RH"),
            start_point_values=(95.0, 20.0),
            effectiveness=0.0,
        )
        result = solver.solve(inp)
        assert result.end_point["Tdb"] == pytest.approx(95.0, abs=0.1)

    def test_horizontal_path(self):
        """Path should be horizontal (all points have same W)."""
        solver = IndirectEvaporativeSolver()
        inp = ProcessInput(
            process_type=ProcessType.INDIRECT_EVAPORATIVE,
            unit_system="IP",
            pressure=14.696,
            start_point_pair=("Tdb", "RH"),
            start_point_values=(95.0, 20.0),
            effectiveness=0.7,
        )
        result = solver.solve(inp)
        W_values = [p.W for p in result.path_points]
        assert all(abs(w - W_values[0]) < 0.0001 for w in W_values)


# ────────────────────────────────────────────────────────────────────────────
# Indirect-Direct Two-Stage
# ────────────────────────────────────────────────────────────────────────────

class TestIndirectDirectEvaporative:
    """Two-stage IDEC: 70% IEC then 80% DEC."""

    @pytest.fixture()
    def result(self):
        solver = IndirectDirectEvaporativeSolver()
        inp = ProcessInput(
            process_type=ProcessType.INDIRECT_DIRECT_EVAPORATIVE,
            unit_system="IP",
            pressure=14.696,
            start_point_pair=("Tdb", "RH"),
            start_point_values=(100.0, 15.0),
            iec_effectiveness=0.7,
            dec_effectiveness=0.8,
        )
        return solver.solve(inp)

    def test_tdb_decreases(self, result):
        assert result.end_point["Tdb"] < result.start_point["Tdb"]

    def test_w_increases(self, result):
        """DEC stage adds moisture (W increases from intermediate onward)."""
        assert result.end_point["W"] > result.start_point["W"]

    def test_deeper_cooling_than_either_alone(self, result):
        """Two-stage should cool more than IEC alone."""
        # IEC alone at 70% effectiveness
        iec_solver = IndirectEvaporativeSolver()
        iec_result = iec_solver.solve(ProcessInput(
            process_type=ProcessType.INDIRECT_EVAPORATIVE,
            unit_system="IP",
            pressure=14.696,
            start_point_pair=("Tdb", "RH"),
            start_point_values=(100.0, 15.0),
            effectiveness=0.7,
        ))
        assert result.end_point["Tdb"] < iec_result.end_point["Tdb"]

    def test_intermediate_in_metadata(self, result):
        assert "intermediate_Tdb" in result.metadata
        assert "intermediate_RH" in result.metadata
        # Intermediate Tdb should be between start and end
        assert result.start_point["Tdb"] > result.metadata["intermediate_Tdb"] > result.end_point["Tdb"]

    def test_process_type(self, result):
        assert result.process_type == ProcessType.INDIRECT_DIRECT_EVAPORATIVE

    def test_no_warnings(self, result):
        assert len(result.warnings) == 0

    def test_path_has_two_segments(self, result):
        """Path should have points from both IEC (horizontal) and DEC (curved)."""
        pts = result.path_points
        assert len(pts) >= 15  # 6 + 14 (minus 1 duplicate at junction)

        # First few points should have roughly constant W (IEC segment)
        W_iec = [p.W for p in pts[:5]]
        assert all(abs(w - W_iec[0]) < 0.0002 for w in W_iec)

        # Last few points should have increasing W (DEC segment)
        W_dec = [p.W for p in pts[-5:]]
        for i in range(1, len(W_dec)):
            assert W_dec[i] >= W_dec[i - 1] - 1e-7


class TestIndirectDirectWithSecondary:
    """IDEC with a specific secondary airstream."""

    @pytest.fixture()
    def result(self):
        solver = IndirectDirectEvaporativeSolver()
        inp = ProcessInput(
            process_type=ProcessType.INDIRECT_DIRECT_EVAPORATIVE,
            unit_system="IP",
            pressure=14.696,
            start_point_pair=("Tdb", "RH"),
            start_point_values=(100.0, 15.0),
            iec_effectiveness=0.6,
            dec_effectiveness=0.7,
            secondary_air_pair=("Tdb", "RH"),
            secondary_air_values=(85.0, 40.0),
        )
        return solver.solve(inp)

    def test_tdb_decreases(self, result):
        assert result.end_point["Tdb"] < 100.0

    def test_secondary_twb_in_metadata(self, result):
        assert "secondary_Twb" in result.metadata


class TestIndirectDirectSI:
    """IDEC in SI units."""

    @pytest.fixture()
    def result(self):
        solver = IndirectDirectEvaporativeSolver()
        inp = ProcessInput(
            process_type=ProcessType.INDIRECT_DIRECT_EVAPORATIVE,
            unit_system="SI",
            pressure=101325.0,
            start_point_pair=("Tdb", "RH"),
            start_point_values=(40.0, 15.0),
            iec_effectiveness=0.7,
            dec_effectiveness=0.8,
        )
        return solver.solve(inp)

    def test_tdb_decreases(self, result):
        assert result.end_point["Tdb"] < 40.0

    def test_unit_system(self, result):
        assert result.unit_system == "SI"


class TestIndirectDirectEdgeCases:
    """Edge cases for IDEC."""

    def test_missing_iec_effectiveness(self):
        solver = IndirectDirectEvaporativeSolver()
        inp = ProcessInput(
            process_type=ProcessType.INDIRECT_DIRECT_EVAPORATIVE,
            start_point_pair=("Tdb", "RH"),
            start_point_values=(100.0, 15.0),
            dec_effectiveness=0.8,
        )
        with pytest.raises(ValueError, match="iec_effectiveness"):
            solver.solve(inp)

    def test_missing_dec_effectiveness(self):
        solver = IndirectDirectEvaporativeSolver()
        inp = ProcessInput(
            process_type=ProcessType.INDIRECT_DIRECT_EVAPORATIVE,
            start_point_pair=("Tdb", "RH"),
            start_point_values=(100.0, 15.0),
            iec_effectiveness=0.7,
        )
        with pytest.raises(ValueError, match="dec_effectiveness"):
            solver.solve(inp)

    def test_iec_effectiveness_out_of_range(self):
        solver = IndirectDirectEvaporativeSolver()
        inp = ProcessInput(
            process_type=ProcessType.INDIRECT_DIRECT_EVAPORATIVE,
            start_point_pair=("Tdb", "RH"),
            start_point_values=(100.0, 15.0),
            iec_effectiveness=1.5,
            dec_effectiveness=0.8,
        )
        with pytest.raises(ValueError, match="between 0 and 1"):
            solver.solve(inp)

    def test_both_zero(self):
        """Both stages at zero → no change."""
        solver = IndirectDirectEvaporativeSolver()
        inp = ProcessInput(
            process_type=ProcessType.INDIRECT_DIRECT_EVAPORATIVE,
            unit_system="IP",
            pressure=14.696,
            start_point_pair=("Tdb", "RH"),
            start_point_values=(100.0, 15.0),
            iec_effectiveness=0.0,
            dec_effectiveness=0.0,
        )
        result = solver.solve(inp)
        assert result.end_point["Tdb"] == pytest.approx(100.0, abs=0.1)

    def test_iec_only(self):
        """IEC at 70%, DEC at 0% → same as IEC alone."""
        solver_idec = IndirectDirectEvaporativeSolver()
        result_idec = solver_idec.solve(ProcessInput(
            process_type=ProcessType.INDIRECT_DIRECT_EVAPORATIVE,
            unit_system="IP",
            pressure=14.696,
            start_point_pair=("Tdb", "RH"),
            start_point_values=(100.0, 15.0),
            iec_effectiveness=0.7,
            dec_effectiveness=0.0,
        ))

        solver_iec = IndirectEvaporativeSolver()
        result_iec = solver_iec.solve(ProcessInput(
            process_type=ProcessType.INDIRECT_EVAPORATIVE,
            unit_system="IP",
            pressure=14.696,
            start_point_pair=("Tdb", "RH"),
            start_point_values=(100.0, 15.0),
            effectiveness=0.7,
        ))

        assert result_idec.end_point["Tdb"] == pytest.approx(
            result_iec.end_point["Tdb"], abs=0.5
        )
        assert result_idec.end_point["W"] == pytest.approx(
            result_iec.end_point["W"], abs=0.0005
        )
