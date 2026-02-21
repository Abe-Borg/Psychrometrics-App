"""
Tests for the adiabatic mixing process solver.

Covers basic mixing, equal mixing, extreme fractions, lever rule verification,
metadata correctness, SI units, edge cases, and validation errors.
"""

import pytest
from app.config import UnitSystem, DEFAULT_PRESSURE_IP, DEFAULT_PRESSURE_SI
from app.engine.processes.mixing import MixingSolver
from app.models.process import ProcessInput, ProcessType


def approx(value: float, rel_tol: float = 0.01, abs_tol: float = 0.1):
    return pytest.approx(value, rel=rel_tol, abs=abs_tol)


@pytest.fixture
def solver():
    return MixingSolver()


def _make_input(**overrides):
    """Helper to build a ProcessInput for mixing with sensible defaults."""
    defaults = dict(
        process_type=ProcessType.ADIABATIC_MIXING,
        unit_system=UnitSystem.IP,
        pressure=DEFAULT_PRESSURE_IP,
        start_point_pair=("Tdb", "Twb"),
        start_point_values=(95.0, 75.0),    # hot humid outdoor air
        stream2_point_pair=("Tdb", "RH"),
        stream2_point_values=(75.0, 50.0),  # conditioned return air
        mixing_fraction=0.30,               # 30% outdoor air
    )
    defaults.update(overrides)
    return ProcessInput(**defaults)


# ---------------------------------------------------------------------------
# Basic mixing: 30% OA at 95°F/75wb + 70% RA at 75°F/50%RH
# ---------------------------------------------------------------------------

class TestBasicMixing:

    def setup_method(self):
        solver = MixingSolver()
        self.result = solver.solve(_make_input())

    def test_process_type(self):
        assert self.result.process_type == ProcessType.ADIABATIC_MIXING

    def test_mixed_tdb(self):
        """30% of 95 + 70% of 75 = 81°F (approximately, exact via enthalpy)."""
        assert self.result.end_point["Tdb"] == approx(81.0, abs_tol=1.0)

    def test_mixed_w_between_streams(self):
        """Mixed W should be between stream 1 W and stream 2 W."""
        W_1 = self.result.start_point["W"]
        W_2 = self.result.metadata["stream2"]["W"]
        W_mix = self.result.end_point["W"]
        assert min(W_1, W_2) <= W_mix <= max(W_1, W_2)

    def test_mixed_h_between_streams(self):
        """Mixed h should be between stream 1 h and stream 2 h."""
        h_1 = self.result.start_point["h"]
        h_2 = self.result.metadata["stream2"]["h"]
        h_mix = self.result.end_point["h"]
        assert min(h_1, h_2) <= h_mix <= max(h_1, h_2)

    def test_path_has_points(self):
        assert len(self.result.path_points) >= 3

    def test_no_warnings(self):
        assert len(self.result.warnings) == 0


# ---------------------------------------------------------------------------
# Equal mixing: 50/50
# ---------------------------------------------------------------------------

class TestEqualMixing:

    def setup_method(self):
        solver = MixingSolver()
        self.result = solver.solve(_make_input(mixing_fraction=0.50))

    def test_mixed_tdb_is_midpoint(self):
        """50/50 mix → Tdb_mix ≈ average of Tdb_1 and Tdb_2."""
        Tdb_1 = self.result.start_point["Tdb"]
        Tdb_2 = self.result.metadata["stream2"]["Tdb"]
        expected_mid = (Tdb_1 + Tdb_2) / 2
        assert self.result.end_point["Tdb"] == approx(expected_mid, abs_tol=0.5)

    def test_mixed_w_is_midpoint(self):
        W_1 = self.result.start_point["W"]
        W_2 = self.result.metadata["stream2"]["W"]
        W_mix = self.result.end_point["W"]
        expected = (W_1 + W_2) / 2
        assert W_mix == approx(expected, rel_tol=0.001, abs_tol=0.0001)

    def test_mixed_h_is_midpoint(self):
        h_1 = self.result.start_point["h"]
        h_2 = self.result.metadata["stream2"]["h"]
        h_mix = self.result.end_point["h"]
        expected = (h_1 + h_2) / 2
        assert h_mix == approx(expected, rel_tol=0.001, abs_tol=0.05)


# ---------------------------------------------------------------------------
# Extreme fractions: nearly all one stream
# ---------------------------------------------------------------------------

class TestExtremeFractions:

    def test_high_fraction_near_stream1(self):
        solver = MixingSolver()
        result = solver.solve(_make_input(mixing_fraction=0.99))
        Tdb_1 = result.start_point["Tdb"]
        assert result.end_point["Tdb"] == approx(Tdb_1, abs_tol=0.5)

    def test_low_fraction_near_stream2(self):
        solver = MixingSolver()
        result = solver.solve(_make_input(mixing_fraction=0.01))
        Tdb_2 = result.metadata["stream2"]["Tdb"]
        assert result.end_point["Tdb"] == approx(Tdb_2, abs_tol=0.5)


# ---------------------------------------------------------------------------
# Lever rule: mixed point position on the line
# ---------------------------------------------------------------------------

class TestLeverRule:
    """
    The lever rule says:
        (Tdb_mix - Tdb_2) / (Tdb_1 - Tdb_2) = f
        (W_mix - W_2) / (W_1 - W_2) = f
        (h_mix - h_2) / (h_1 - h_2) = f
    """

    def setup_method(self):
        solver = MixingSolver()
        self.f = 0.30
        self.result = solver.solve(_make_input(mixing_fraction=self.f))

    def test_lever_tdb(self):
        Tdb_1 = self.result.start_point["Tdb"]
        Tdb_2 = self.result.metadata["stream2"]["Tdb"]
        Tdb_mix = self.result.end_point["Tdb"]
        ratio = (Tdb_mix - Tdb_2) / (Tdb_1 - Tdb_2)
        assert ratio == approx(self.f, rel_tol=0.01, abs_tol=0.01)

    def test_lever_w(self):
        W_1 = self.result.start_point["W"]
        W_2 = self.result.metadata["stream2"]["W"]
        W_mix = self.result.end_point["W"]
        ratio = (W_mix - W_2) / (W_1 - W_2)
        assert ratio == approx(self.f, rel_tol=0.01, abs_tol=0.01)

    def test_lever_h(self):
        h_1 = self.result.start_point["h"]
        h_2 = self.result.metadata["stream2"]["h"]
        h_mix = self.result.end_point["h"]
        ratio = (h_mix - h_2) / (h_1 - h_2)
        assert ratio == approx(self.f, rel_tol=0.01, abs_tol=0.01)


# ---------------------------------------------------------------------------
# Metadata
# ---------------------------------------------------------------------------

class TestMetadata:

    def setup_method(self):
        solver = MixingSolver()
        self.result = solver.solve(_make_input(mixing_fraction=0.30))

    def test_stream2_in_metadata(self):
        assert "stream2" in self.result.metadata
        assert "Tdb" in self.result.metadata["stream2"]
        assert "W" in self.result.metadata["stream2"]

    def test_mixing_fraction_echoed(self):
        assert self.result.metadata["mixing_fraction"] == approx(0.30)

    def test_w_mix_in_metadata(self):
        assert "W_mix" in self.result.metadata

    def test_h_mix_in_metadata(self):
        assert "h_mix" in self.result.metadata

    def test_tdb_mix_in_metadata(self):
        assert "Tdb_mix" in self.result.metadata

    def test_w_mix_display_in_metadata(self):
        assert "W_mix_display" in self.result.metadata

    def test_w_mix_matches_end_point(self):
        """Metadata W_mix should match the end_point W."""
        assert self.result.metadata["W_mix"] == approx(
            self.result.end_point["W"], rel_tol=0.001, abs_tol=0.0001
        )

    def test_h_mix_matches_end_point(self):
        assert self.result.metadata["h_mix"] == approx(
            self.result.end_point["h"], rel_tol=0.001, abs_tol=0.05
        )


# ---------------------------------------------------------------------------
# SI units
# ---------------------------------------------------------------------------

class TestMixingSI:

    def setup_method(self):
        solver = MixingSolver()
        self.result = solver.solve(ProcessInput(
            process_type=ProcessType.ADIABATIC_MIXING,
            unit_system=UnitSystem.SI,
            pressure=DEFAULT_PRESSURE_SI,
            start_point_pair=("Tdb", "Twb"),
            start_point_values=(35.0, 24.0),   # hot humid outdoor (SI)
            stream2_point_pair=("Tdb", "RH"),
            stream2_point_values=(24.0, 50.0),  # conditioned return (SI)
            mixing_fraction=0.30,
        ))

    def test_unit_system(self):
        assert self.result.unit_system == UnitSystem.SI

    def test_mixed_tdb_between(self):
        Tdb_1 = self.result.start_point["Tdb"]
        Tdb_2 = self.result.metadata["stream2"]["Tdb"]
        Tdb_mix = self.result.end_point["Tdb"]
        assert min(Tdb_1, Tdb_2) <= Tdb_mix <= max(Tdb_1, Tdb_2)

    def test_mixed_w_between(self):
        W_1 = self.result.start_point["W"]
        W_2 = self.result.metadata["stream2"]["W"]
        W_mix = self.result.end_point["W"]
        assert min(W_1, W_2) <= W_mix <= max(W_1, W_2)

    def test_lever_rule_tdb(self):
        Tdb_1 = self.result.start_point["Tdb"]
        Tdb_2 = self.result.metadata["stream2"]["Tdb"]
        Tdb_mix = self.result.end_point["Tdb"]
        ratio = (Tdb_mix - Tdb_2) / (Tdb_1 - Tdb_2)
        assert ratio == approx(0.30, rel_tol=0.01, abs_tol=0.01)


# ---------------------------------------------------------------------------
# Identical streams
# ---------------------------------------------------------------------------

class TestIdenticalStreams:

    def test_same_state_mixing(self):
        """Mixing two identical streams should produce the same state."""
        solver = MixingSolver()
        result = solver.solve(ProcessInput(
            process_type=ProcessType.ADIABATIC_MIXING,
            unit_system=UnitSystem.IP,
            pressure=DEFAULT_PRESSURE_IP,
            start_point_pair=("Tdb", "RH"),
            start_point_values=(75.0, 50.0),
            stream2_point_pair=("Tdb", "RH"),
            stream2_point_values=(75.0, 50.0),
            mixing_fraction=0.50,
        ))
        assert result.end_point["Tdb"] == approx(75.0)
        assert result.end_point["RH"] == approx(50.0)


# ---------------------------------------------------------------------------
# Edge cases and validation errors
# ---------------------------------------------------------------------------

class TestEdgeCases:

    def test_missing_stream2_pair(self):
        solver = MixingSolver()
        with pytest.raises(ValueError, match="stream2_point_pair"):
            solver.solve(ProcessInput(
                process_type=ProcessType.ADIABATIC_MIXING,
                start_point_pair=("Tdb", "RH"),
                start_point_values=(80.0, 50.0),
                mixing_fraction=0.50,
            ))

    def test_missing_mixing_fraction(self):
        solver = MixingSolver()
        with pytest.raises(ValueError, match="mixing_fraction"):
            solver.solve(ProcessInput(
                process_type=ProcessType.ADIABATIC_MIXING,
                start_point_pair=("Tdb", "RH"),
                start_point_values=(80.0, 50.0),
                stream2_point_pair=("Tdb", "RH"),
                stream2_point_values=(75.0, 50.0),
            ))

    def test_fraction_negative(self):
        solver = MixingSolver()
        with pytest.raises(ValueError, match="between 0 and 1"):
            solver.solve(_make_input(mixing_fraction=-0.1))

    def test_fraction_above_one(self):
        solver = MixingSolver()
        with pytest.raises(ValueError, match="between 0 and 1"):
            solver.solve(_make_input(mixing_fraction=1.5))

    def test_fraction_zero_warns(self):
        solver = MixingSolver()
        result = solver.solve(_make_input(mixing_fraction=0.0))
        assert len(result.warnings) > 0
        assert "stream 2" in result.warnings[0].lower()

    def test_fraction_one_warns(self):
        solver = MixingSolver()
        result = solver.solve(_make_input(mixing_fraction=1.0))
        assert len(result.warnings) > 0
        assert "stream 1" in result.warnings[0].lower()
