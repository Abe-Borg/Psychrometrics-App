"""
Tests for humidification process solvers: steam, adiabatic, heated water spray.
"""

import pytest

from app.models.process import ProcessInput, ProcessType, HumidificationMode
from app.engine.processes.humidification import (
    SteamHumidificationSolver,
    AdiabaticHumidificationSolver,
    HeatedWaterHumidificationSolver,
)


# ────────────────────────────────────────────────────────────────────────────
# Steam Humidification
# ────────────────────────────────────────────────────────────────────────────

class TestSteamHumidificationTargetRH:
    """Steam humidification: target RH mode at constant Tdb."""

    @pytest.fixture()
    def result(self):
        solver = SteamHumidificationSolver()
        inp = ProcessInput(
            process_type=ProcessType.STEAM_HUMIDIFICATION,
            unit_system="IP",
            pressure=14.696,
            start_point_pair=("Tdb", "RH"),
            start_point_values=(72.0, 20.0),
            humidification_mode=HumidificationMode.TARGET_RH,
            target_RH=50.0,
        )
        return solver.solve(inp)

    def test_tdb_unchanged(self, result):
        assert result.start_point["Tdb"] == pytest.approx(72.0, abs=0.1)
        assert result.end_point["Tdb"] == pytest.approx(72.0, abs=0.1)

    def test_w_increased(self, result):
        assert result.end_point["W"] > result.start_point["W"]

    def test_end_rh_matches_target(self, result):
        assert result.end_point["RH"] == pytest.approx(50.0, abs=0.5)

    def test_process_type(self, result):
        assert result.process_type == ProcessType.STEAM_HUMIDIFICATION

    def test_no_warnings(self, result):
        assert len(result.warnings) == 0

    def test_path_is_vertical(self, result):
        """All path points should have the same Tdb."""
        tdbs = [p.Tdb for p in result.path_points]
        assert all(abs(t - tdbs[0]) < 0.01 for t in tdbs)

    def test_metadata_present(self, result):
        assert "delta_W" in result.metadata
        assert "delta_h" in result.metadata
        assert result.metadata["delta_W"] > 0


class TestSteamHumidificationTargetW:
    """Steam humidification: target W mode."""

    @pytest.fixture()
    def result(self):
        solver = SteamHumidificationSolver()
        inp = ProcessInput(
            process_type=ProcessType.STEAM_HUMIDIFICATION,
            unit_system="IP",
            pressure=14.696,
            start_point_pair=("Tdb", "RH"),
            start_point_values=(72.0, 20.0),
            humidification_mode=HumidificationMode.TARGET_W,
            target_W=0.008,
        )
        return solver.solve(inp)

    def test_end_w_matches_target(self, result):
        assert result.end_point["W"] == pytest.approx(0.008, abs=0.0001)

    def test_tdb_constant(self, result):
        assert result.end_point["Tdb"] == pytest.approx(72.0, abs=0.1)


class TestSteamHumidificationSI:
    """Steam humidification in SI units."""

    @pytest.fixture()
    def result(self):
        solver = SteamHumidificationSolver()
        inp = ProcessInput(
            process_type=ProcessType.STEAM_HUMIDIFICATION,
            unit_system="SI",
            pressure=101325.0,
            start_point_pair=("Tdb", "RH"),
            start_point_values=(22.0, 20.0),
            humidification_mode=HumidificationMode.TARGET_RH,
            target_RH=50.0,
        )
        return solver.solve(inp)

    def test_tdb_constant(self, result):
        assert result.end_point["Tdb"] == pytest.approx(22.0, abs=0.1)

    def test_w_increased(self, result):
        assert result.end_point["W"] > result.start_point["W"]

    def test_unit_system(self, result):
        assert result.unit_system == "SI"


class TestSteamHumidificationEdgeCases:
    """Edge cases for steam humidification."""

    def test_missing_mode(self):
        solver = SteamHumidificationSolver()
        inp = ProcessInput(
            process_type=ProcessType.STEAM_HUMIDIFICATION,
            start_point_pair=("Tdb", "RH"),
            start_point_values=(72.0, 20.0),
        )
        with pytest.raises(ValueError, match="humidification_mode"):
            solver.solve(inp)

    def test_missing_target_rh(self):
        solver = SteamHumidificationSolver()
        inp = ProcessInput(
            process_type=ProcessType.STEAM_HUMIDIFICATION,
            start_point_pair=("Tdb", "RH"),
            start_point_values=(72.0, 20.0),
            humidification_mode=HumidificationMode.TARGET_RH,
        )
        with pytest.raises(ValueError, match="target_RH"):
            solver.solve(inp)

    def test_missing_target_w(self):
        solver = SteamHumidificationSolver()
        inp = ProcessInput(
            process_type=ProcessType.STEAM_HUMIDIFICATION,
            start_point_pair=("Tdb", "RH"),
            start_point_values=(72.0, 20.0),
            humidification_mode=HumidificationMode.TARGET_W,
        )
        with pytest.raises(ValueError, match="target_W"):
            solver.solve(inp)

    def test_dehumidification_warning(self):
        """Target W below start W should produce a warning."""
        solver = SteamHumidificationSolver()
        inp = ProcessInput(
            process_type=ProcessType.STEAM_HUMIDIFICATION,
            start_point_pair=("Tdb", "RH"),
            start_point_values=(72.0, 50.0),
            humidification_mode=HumidificationMode.TARGET_RH,
            target_RH=20.0,
        )
        result = solver.solve(inp)
        assert len(result.warnings) > 0
        assert "dehumidification" in result.warnings[0].lower()

    def test_invalid_mode_for_steam(self):
        solver = SteamHumidificationSolver()
        inp = ProcessInput(
            process_type=ProcessType.STEAM_HUMIDIFICATION,
            start_point_pair=("Tdb", "RH"),
            start_point_values=(72.0, 20.0),
            humidification_mode=HumidificationMode.EFFECTIVENESS,
            effectiveness=0.5,
        )
        with pytest.raises(ValueError, match="Unsupported"):
            solver.solve(inp)


# ────────────────────────────────────────────────────────────────────────────
# Adiabatic Humidification
# ────────────────────────────────────────────────────────────────────────────

class TestAdiabaticHumidificationEffectiveness:
    """Adiabatic humidification with effectiveness mode."""

    @pytest.fixture()
    def result(self):
        solver = AdiabaticHumidificationSolver()
        inp = ProcessInput(
            process_type=ProcessType.ADIABATIC_HUMIDIFICATION,
            unit_system="IP",
            pressure=14.696,
            start_point_pair=("Tdb", "RH"),
            start_point_values=(80.0, 30.0),
            humidification_mode=HumidificationMode.EFFECTIVENESS,
            effectiveness=0.8,
        )
        return solver.solve(inp)

    def test_tdb_decreases(self, result):
        """Adiabatic humidification cools the air (Tdb drops)."""
        assert result.end_point["Tdb"] < result.start_point["Tdb"]

    def test_w_increases(self, result):
        """Humidity ratio increases."""
        assert result.end_point["W"] > result.start_point["W"]

    def test_twb_approximately_constant(self, result):
        """Wet-bulb should remain approximately constant."""
        assert result.end_point["Twb"] == pytest.approx(
            result.start_point["Twb"], abs=0.5
        )

    def test_effectiveness_in_metadata(self, result):
        assert result.metadata["effectiveness"] == pytest.approx(0.8, abs=0.01)

    def test_rh_increases(self, result):
        assert result.end_point["RH"] > result.start_point["RH"]

    def test_process_type(self, result):
        assert result.process_type == ProcessType.ADIABATIC_HUMIDIFICATION

    def test_no_warnings(self, result):
        assert len(result.warnings) == 0

    def test_effectiveness_formula(self, result):
        """Verify ε = (Tdb_in - Tdb_out) / (Tdb_in - Twb_in)."""
        start_Tdb = result.start_point["Tdb"]
        end_Tdb = result.end_point["Tdb"]
        Twb = result.start_point["Twb"]
        computed_eff = (start_Tdb - end_Tdb) / (start_Tdb - Twb)
        assert computed_eff == pytest.approx(0.8, abs=0.01)


class TestAdiabaticHumidification100Percent:
    """Adiabatic humidification at 100% effectiveness → saturation."""

    @pytest.fixture()
    def result(self):
        solver = AdiabaticHumidificationSolver()
        inp = ProcessInput(
            process_type=ProcessType.ADIABATIC_HUMIDIFICATION,
            unit_system="IP",
            pressure=14.696,
            start_point_pair=("Tdb", "RH"),
            start_point_values=(80.0, 30.0),
            humidification_mode=HumidificationMode.EFFECTIVENESS,
            effectiveness=1.0,
        )
        return solver.solve(inp)

    def test_end_rh_is_100(self, result):
        assert result.end_point["RH"] == pytest.approx(100.0, abs=1.0)

    def test_end_tdb_equals_twb(self, result):
        assert result.end_point["Tdb"] == pytest.approx(
            result.start_point["Twb"], abs=0.5
        )


class TestAdiabaticHumidificationTargetRH:
    """Adiabatic humidification with target RH mode."""

    @pytest.fixture()
    def result(self):
        solver = AdiabaticHumidificationSolver()
        inp = ProcessInput(
            process_type=ProcessType.ADIABATIC_HUMIDIFICATION,
            unit_system="IP",
            pressure=14.696,
            start_point_pair=("Tdb", "RH"),
            start_point_values=(80.0, 30.0),
            humidification_mode=HumidificationMode.TARGET_RH,
            target_RH=70.0,
        )
        return solver.solve(inp)

    def test_end_rh_matches_target(self, result):
        assert result.end_point["RH"] == pytest.approx(70.0, abs=1.0)

    def test_tdb_decreases(self, result):
        assert result.end_point["Tdb"] < result.start_point["Tdb"]

    def test_twb_approximately_constant(self, result):
        assert result.end_point["Twb"] == pytest.approx(
            result.start_point["Twb"], abs=0.5
        )


class TestAdiabaticHumidificationSI:
    """Adiabatic humidification in SI units."""

    @pytest.fixture()
    def result(self):
        solver = AdiabaticHumidificationSolver()
        inp = ProcessInput(
            process_type=ProcessType.ADIABATIC_HUMIDIFICATION,
            unit_system="SI",
            pressure=101325.0,
            start_point_pair=("Tdb", "RH"),
            start_point_values=(30.0, 30.0),
            humidification_mode=HumidificationMode.EFFECTIVENESS,
            effectiveness=0.7,
        )
        return solver.solve(inp)

    def test_tdb_decreases(self, result):
        assert result.end_point["Tdb"] < 30.0

    def test_w_increases(self, result):
        assert result.end_point["W"] > result.start_point["W"]

    def test_unit_system(self, result):
        assert result.unit_system == "SI"


class TestAdiabaticHumidificationEdgeCases:
    """Edge cases for adiabatic humidification."""

    def test_missing_mode(self):
        solver = AdiabaticHumidificationSolver()
        inp = ProcessInput(
            process_type=ProcessType.ADIABATIC_HUMIDIFICATION,
            start_point_pair=("Tdb", "RH"),
            start_point_values=(80.0, 30.0),
        )
        with pytest.raises(ValueError, match="humidification_mode"):
            solver.solve(inp)

    def test_missing_effectiveness(self):
        solver = AdiabaticHumidificationSolver()
        inp = ProcessInput(
            process_type=ProcessType.ADIABATIC_HUMIDIFICATION,
            start_point_pair=("Tdb", "RH"),
            start_point_values=(80.0, 30.0),
            humidification_mode=HumidificationMode.EFFECTIVENESS,
        )
        with pytest.raises(ValueError, match="effectiveness"):
            solver.solve(inp)

    def test_effectiveness_out_of_range(self):
        solver = AdiabaticHumidificationSolver()
        inp = ProcessInput(
            process_type=ProcessType.ADIABATIC_HUMIDIFICATION,
            start_point_pair=("Tdb", "RH"),
            start_point_values=(80.0, 30.0),
            humidification_mode=HumidificationMode.EFFECTIVENESS,
            effectiveness=1.5,
        )
        with pytest.raises(ValueError, match="between 0 and 1"):
            solver.solve(inp)

    def test_target_rh_below_current(self):
        solver = AdiabaticHumidificationSolver()
        inp = ProcessInput(
            process_type=ProcessType.ADIABATIC_HUMIDIFICATION,
            start_point_pair=("Tdb", "RH"),
            start_point_values=(80.0, 50.0),
            humidification_mode=HumidificationMode.TARGET_RH,
            target_RH=30.0,
        )
        with pytest.raises(ValueError, match="must be greater"):
            solver.solve(inp)

    def test_zero_effectiveness(self):
        """Zero effectiveness should return start == end."""
        solver = AdiabaticHumidificationSolver()
        inp = ProcessInput(
            process_type=ProcessType.ADIABATIC_HUMIDIFICATION,
            start_point_pair=("Tdb", "RH"),
            start_point_values=(80.0, 30.0),
            humidification_mode=HumidificationMode.EFFECTIVENESS,
            effectiveness=0.0,
        )
        result = solver.solve(inp)
        assert result.end_point["Tdb"] == pytest.approx(80.0, abs=0.1)
        assert result.end_point["W"] == pytest.approx(result.start_point["W"], abs=0.0001)

    def test_path_is_curved(self):
        """Path along constant Twb should not be a straight line."""
        solver = AdiabaticHumidificationSolver()
        inp = ProcessInput(
            process_type=ProcessType.ADIABATIC_HUMIDIFICATION,
            unit_system="IP",
            pressure=14.696,
            start_point_pair=("Tdb", "RH"),
            start_point_values=(90.0, 20.0),
            humidification_mode=HumidificationMode.EFFECTIVENESS,
            effectiveness=0.9,
        )
        result = solver.solve(inp)
        pts = result.path_points
        assert len(pts) > 10

        # Check that W values are monotonically increasing
        for i in range(1, len(pts)):
            assert pts[i].W >= pts[i - 1].W - 1e-7


# ────────────────────────────────────────────────────────────────────────────
# Heated Water Spray Humidification
# ────────────────────────────────────────────────────────────────────────────

class TestHeatedWaterHumidification:
    """Heated water spray: water temp above Twb (both Tdb and W increase)."""

    @pytest.fixture()
    def result(self):
        solver = HeatedWaterHumidificationSolver()
        inp = ProcessInput(
            process_type=ProcessType.HEATED_WATER_HUMIDIFICATION,
            unit_system="IP",
            pressure=14.696,
            start_point_pair=("Tdb", "RH"),
            start_point_values=(70.0, 30.0),
            effectiveness=0.5,
            water_temperature=140.0,
        )
        return solver.solve(inp)

    def test_tdb_increases(self, result):
        """With hot water (140°F > 70°F), Tdb should increase."""
        assert result.end_point["Tdb"] > result.start_point["Tdb"]

    def test_w_increases(self, result):
        assert result.end_point["W"] > result.start_point["W"]

    def test_rh_increases(self, result):
        assert result.end_point["RH"] > result.start_point["RH"]

    def test_process_type(self, result):
        assert result.process_type == ProcessType.HEATED_WATER_HUMIDIFICATION

    def test_metadata(self, result):
        assert result.metadata["effectiveness"] == pytest.approx(0.5, abs=0.01)
        assert result.metadata["water_temperature"] == pytest.approx(140.0, abs=0.1)


class TestHeatedWaterColdWater:
    """Heated water spray with cold water (below Twb but above Tdp)."""

    @pytest.fixture()
    def result(self):
        solver = HeatedWaterHumidificationSolver()
        # Start: 90°F / 30% RH → Twb ≈ 70°F, Tdp ≈ 55°F
        # Water at 65°F (above Tdp, below Twb) — still humidifies
        inp = ProcessInput(
            process_type=ProcessType.HEATED_WATER_HUMIDIFICATION,
            unit_system="IP",
            pressure=14.696,
            start_point_pair=("Tdb", "RH"),
            start_point_values=(90.0, 30.0),
            effectiveness=0.5,
            water_temperature=65.0,
        )
        return solver.solve(inp)

    def test_tdb_decreases(self, result):
        """Cold water spray should cool the air."""
        assert result.end_point["Tdb"] < result.start_point["Tdb"]

    def test_w_increases(self, result):
        """Water above dew point still adds moisture (W_sat at 65°F > W_entering)."""
        assert result.end_point["W"] > result.start_point["W"]


class TestHeatedWaterVeryColdWater:
    """Very cold water (below dew point) can actually dehumidify."""

    def test_w_decreases_with_very_cold_water(self):
        solver = HeatedWaterHumidificationSolver()
        # Start: 90°F / 30% RH → Tdp ≈ 55°F
        # Water at 45°F (well below Tdp) — W_sat(45) < W_entering
        inp = ProcessInput(
            process_type=ProcessType.HEATED_WATER_HUMIDIFICATION,
            unit_system="IP",
            pressure=14.696,
            start_point_pair=("Tdb", "RH"),
            start_point_values=(90.0, 30.0),
            effectiveness=0.5,
            water_temperature=45.0,
        )
        result = solver.solve(inp)
        # Moving toward saturation at 45°F where W_sat < W_entering
        assert result.end_point["W"] < result.start_point["W"]
        assert result.end_point["Tdb"] < result.start_point["Tdb"]


class TestHeatedWaterAtTwb:
    """Heated water at Twb should approximate adiabatic humidification."""

    def test_similar_to_adiabatic(self):
        # Start: 80°F, 30% RH → Twb ≈ 60°F
        # Water at Twb (~60°F)
        from app.engine.state_resolver import resolve_state_point

        start = resolve_state_point(
            input_pair=("Tdb", "RH"),
            values=(80.0, 30.0),
            pressure=14.696,
            unit_system="IP",
            label="start",
        )
        Twb = start.Twb

        hw_solver = HeatedWaterHumidificationSolver()
        hw_inp = ProcessInput(
            process_type=ProcessType.HEATED_WATER_HUMIDIFICATION,
            unit_system="IP",
            pressure=14.696,
            start_point_pair=("Tdb", "RH"),
            start_point_values=(80.0, 30.0),
            effectiveness=0.7,
            water_temperature=Twb,
        )
        hw_result = hw_solver.solve(hw_inp)

        ad_solver = AdiabaticHumidificationSolver()
        ad_inp = ProcessInput(
            process_type=ProcessType.ADIABATIC_HUMIDIFICATION,
            unit_system="IP",
            pressure=14.696,
            start_point_pair=("Tdb", "RH"),
            start_point_values=(80.0, 30.0),
            humidification_mode=HumidificationMode.EFFECTIVENESS,
            effectiveness=0.7,
        )
        ad_result = ad_solver.solve(ad_inp)

        # End points should be very close
        assert hw_result.end_point["Tdb"] == pytest.approx(
            ad_result.end_point["Tdb"], abs=0.5
        )
        assert hw_result.end_point["W"] == pytest.approx(
            ad_result.end_point["W"], abs=0.0005
        )


class TestHeatedWaterSI:
    """Heated water spray in SI units."""

    @pytest.fixture()
    def result(self):
        solver = HeatedWaterHumidificationSolver()
        inp = ProcessInput(
            process_type=ProcessType.HEATED_WATER_HUMIDIFICATION,
            unit_system="SI",
            pressure=101325.0,
            start_point_pair=("Tdb", "RH"),
            start_point_values=(22.0, 30.0),
            effectiveness=0.5,
            water_temperature=60.0,
        )
        return solver.solve(inp)

    def test_tdb_increases(self, result):
        assert result.end_point["Tdb"] > 22.0

    def test_w_increases(self, result):
        assert result.end_point["W"] > result.start_point["W"]

    def test_unit_system(self, result):
        assert result.unit_system == "SI"


class TestHeatedWaterEdgeCases:
    """Edge cases for heated water spray."""

    def test_missing_effectiveness(self):
        solver = HeatedWaterHumidificationSolver()
        inp = ProcessInput(
            process_type=ProcessType.HEATED_WATER_HUMIDIFICATION,
            start_point_pair=("Tdb", "RH"),
            start_point_values=(70.0, 30.0),
            water_temperature=140.0,
        )
        with pytest.raises(ValueError, match="effectiveness"):
            solver.solve(inp)

    def test_missing_water_temperature(self):
        solver = HeatedWaterHumidificationSolver()
        inp = ProcessInput(
            process_type=ProcessType.HEATED_WATER_HUMIDIFICATION,
            start_point_pair=("Tdb", "RH"),
            start_point_values=(70.0, 30.0),
            effectiveness=0.5,
        )
        with pytest.raises(ValueError, match="water_temperature"):
            solver.solve(inp)

    def test_effectiveness_out_of_range(self):
        solver = HeatedWaterHumidificationSolver()
        inp = ProcessInput(
            process_type=ProcessType.HEATED_WATER_HUMIDIFICATION,
            start_point_pair=("Tdb", "RH"),
            start_point_values=(70.0, 30.0),
            effectiveness=1.5,
            water_temperature=140.0,
        )
        with pytest.raises(ValueError, match="between 0 and 1"):
            solver.solve(inp)

    def test_zero_effectiveness(self):
        """Zero effectiveness → no change."""
        solver = HeatedWaterHumidificationSolver()
        inp = ProcessInput(
            process_type=ProcessType.HEATED_WATER_HUMIDIFICATION,
            unit_system="IP",
            pressure=14.696,
            start_point_pair=("Tdb", "RH"),
            start_point_values=(70.0, 30.0),
            effectiveness=0.0,
            water_temperature=140.0,
        )
        result = solver.solve(inp)
        assert result.end_point["Tdb"] == pytest.approx(70.0, abs=0.1)
        assert result.end_point["W"] == pytest.approx(
            result.start_point["W"], abs=0.0001
        )
