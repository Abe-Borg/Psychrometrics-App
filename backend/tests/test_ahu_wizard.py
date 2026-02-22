"""
Tests for the AHU Wizard engine and API route.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.engine.ahu_wizard import calculate_ahu
from app.models.ahu_wizard import AHUType, AHUWizardInput


client = TestClient(app)


# ── Typical summer design conditions (IP) ──
# OA: 95°F DB / 78°F WB (hot humid)
# RA: 75°F / 50% RH (standard room conditions)
# Supply: 55°F


def _mixed_air_input(**overrides) -> AHUWizardInput:
    """Helper to build a mixed-air AHU input with sensible defaults."""
    defaults = dict(
        ahu_type=AHUType.MIXED_AIR,
        unit_system="IP",
        pressure=14.696,
        oa_Tdb=95.0,
        oa_coincident=78.0,
        oa_input_type="Twb",
        ra_Tdb=75.0,
        ra_RH=50.0,
        oa_fraction=0.3,
        supply_Tdb=55.0,
    )
    defaults.update(overrides)
    return AHUWizardInput(**defaults)


def _full_oa_input(**overrides) -> AHUWizardInput:
    """Helper to build a 100% OA AHU input."""
    defaults = dict(
        ahu_type=AHUType.FULL_OA,
        unit_system="IP",
        pressure=14.696,
        oa_Tdb=95.0,
        oa_coincident=78.0,
        oa_input_type="Twb",
        supply_Tdb=55.0,
    )
    defaults.update(overrides)
    return AHUWizardInput(**defaults)


# ── Engine tests ──


class TestMixedAirAHU:
    """Tests for mixed-air AHU configuration."""

    def test_basic_mixed_air(self):
        result = calculate_ahu(_mixed_air_input())

        assert result.ahu_type == AHUType.MIXED_AIR
        assert result.oa_point is not None
        assert result.ra_point is not None
        assert result.mixed_point is not None
        assert result.coil_leaving is not None
        assert result.supply_point is not None

    def test_mixed_air_oa_fraction(self):
        result = calculate_ahu(_mixed_air_input(oa_fraction=0.3))
        assert result.oa_fraction_used == 0.3

    def test_mixed_air_oa_cfm_ra_cfm(self):
        result = calculate_ahu(_mixed_air_input(
            oa_fraction=None,
            oa_cfm=3000.0,
            ra_cfm=7000.0,
        ))
        assert result.oa_fraction_used == 0.3

    def test_mixed_point_between_oa_and_ra(self):
        result = calculate_ahu(_mixed_air_input(oa_fraction=0.3))
        oa_Tdb = result.oa_point["Tdb"]
        ra_Tdb = result.ra_point["Tdb"]
        mix_Tdb = result.mixed_point["Tdb"]
        # Mixed point Tdb should be between OA and RA
        assert min(oa_Tdb, ra_Tdb) <= mix_Tdb <= max(oa_Tdb, ra_Tdb)

    def test_cooling_loads_positive(self):
        result = calculate_ahu(_mixed_air_input())
        assert result.cooling_Qt > 0
        assert result.cooling_Qs > 0

    def test_shr_valid_range(self):
        result = calculate_ahu(_mixed_air_input())
        assert 0.0 < result.shr <= 1.0

    def test_coil_leaving_at_supply_tdb(self):
        result = calculate_ahu(_mixed_air_input())
        # If no reheat needed, coil leaving should be at supply Tdb
        if not result.needs_reheat:
            assert abs(result.coil_leaving["Tdb"] - 55.0) < 0.5
        else:
            # Supply point should be at target after reheat
            assert abs(result.supply_point["Tdb"] - 55.0) < 0.5

    def test_processes_generated(self):
        result = calculate_ahu(_mixed_air_input())
        # Should have at least mixing + cooling
        assert len(result.processes) >= 2
        types = [p["process_type"] for p in result.processes]
        assert "adiabatic_mixing" in types

    def test_with_reheat(self):
        """Supply Tdb higher than typical coil leaving → reheat."""
        result = calculate_ahu(_mixed_air_input(
            supply_Tdb=55.0,
            supply_RH=50.0,
        ))
        # With 50% RH at 55°F, the coil must cool below 55°F then reheat
        # Check the chain is valid
        assert result.supply_point["Tdb"] == pytest.approx(55.0, abs=0.5)

    def test_with_explicit_supply_rh(self):
        result = calculate_ahu(_mixed_air_input(supply_RH=90.0))
        # Should have a valid supply point at ~90% RH
        assert result.supply_point is not None


class TestFullOAAHU:
    """Tests for 100% outside air (DOAS) configuration."""

    def test_basic_full_oa(self):
        result = calculate_ahu(_full_oa_input())

        assert result.ahu_type == AHUType.FULL_OA
        assert result.ra_point is None
        assert result.mixed_point is None
        assert result.oa_fraction_used == 1.0

    def test_full_oa_cooling(self):
        result = calculate_ahu(_full_oa_input())
        assert result.cooling_Qt > 0

    def test_full_oa_no_mixing_process(self):
        result = calculate_ahu(_full_oa_input())
        types = [p["process_type"] for p in result.processes]
        assert "adiabatic_mixing" not in types

    def test_full_oa_processes(self):
        result = calculate_ahu(_full_oa_input())
        assert len(result.processes) >= 1


class TestSensibleOnlyCooling:
    """Tests for cases with sensible cooling only (no dehumidification)."""

    def test_dry_oa_sensible_only(self):
        # Dry OA: 95°F / 20% RH → low dew point, so cooling to 75°F is sensible only
        result = calculate_ahu(_full_oa_input(
            oa_Tdb=95.0,
            oa_coincident=20.0,
            oa_input_type="RH",
            supply_Tdb=75.0,
        ))
        # W should be essentially unchanged
        oa_W = result.oa_point["W"]
        supply_W = result.supply_point["W"]
        assert abs(oa_W - supply_W) < 1e-5


class TestSIUnits:
    """Test SI unit support."""

    def test_si_mixed_air(self):
        result = calculate_ahu(AHUWizardInput(
            ahu_type=AHUType.MIXED_AIR,
            unit_system="SI",
            pressure=101325.0,
            oa_Tdb=35.0,
            oa_coincident=25.6,
            oa_input_type="Twb",
            ra_Tdb=24.0,
            ra_RH=50.0,
            oa_fraction=0.3,
            supply_Tdb=13.0,
        ))
        assert result.unit_system == "SI"
        assert result.oa_point is not None
        assert result.cooling_Qt > 0

    def test_si_full_oa(self):
        result = calculate_ahu(AHUWizardInput(
            ahu_type=AHUType.FULL_OA,
            unit_system="SI",
            pressure=101325.0,
            oa_Tdb=35.0,
            oa_coincident=25.6,
            oa_input_type="Twb",
            supply_Tdb=13.0,
        ))
        assert result.unit_system == "SI"
        assert result.cooling_Qt > 0


class TestAirflowSizing:
    """Test optional airflow sizing."""

    def test_airflow_from_room_load(self):
        result = calculate_ahu(_mixed_air_input(
            room_sensible_load=60000.0,  # 60k BTU/hr (5 ton sensible)
        ))
        # Should compute supply CFM
        assert result.supply_cfm is not None
        assert result.supply_cfm > 0

    def test_airflow_user_provided(self):
        result = calculate_ahu(_mixed_air_input(
            room_sensible_load=60000.0,
            total_airflow=2000.0,
        ))
        assert result.supply_cfm == 2000.0


class TestNoCoolingNeeded:
    """Tests for edge case where OA is already cool enough."""

    def test_no_cooling(self):
        result = calculate_ahu(_full_oa_input(
            oa_Tdb=50.0,
            oa_coincident=45.0,
            oa_input_type="Twb",
            supply_Tdb=55.0,
        ))
        assert len(result.warnings) > 0
        assert "No cooling needed" in result.warnings[0]


class TestValidationErrors:
    """Test input validation."""

    def test_missing_ra_for_mixed_air(self):
        with pytest.raises(ValueError, match="ra_Tdb and ra_RH"):
            calculate_ahu(AHUWizardInput(
                ahu_type=AHUType.MIXED_AIR,
                oa_Tdb=95.0,
                oa_coincident=78.0,
                supply_Tdb=55.0,
            ))

    def test_missing_mixing_info(self):
        with pytest.raises(ValueError, match="oa_fraction"):
            calculate_ahu(AHUWizardInput(
                ahu_type=AHUType.MIXED_AIR,
                oa_Tdb=95.0,
                oa_coincident=78.0,
                ra_Tdb=75.0,
                ra_RH=50.0,
                supply_Tdb=55.0,
            ))

    def test_invalid_oa_fraction(self):
        with pytest.raises(ValueError, match="OA fraction"):
            calculate_ahu(_mixed_air_input(oa_fraction=1.5))


class TestEconomizerType:
    """Test economizer AHU type (same calculation as mixed_air)."""

    def test_economizer(self):
        result = calculate_ahu(AHUWizardInput(
            ahu_type=AHUType.ECONOMIZER,
            unit_system="IP",
            pressure=14.696,
            oa_Tdb=95.0,
            oa_coincident=78.0,
            oa_input_type="Twb",
            ra_Tdb=75.0,
            ra_RH=50.0,
            oa_fraction=0.3,
            supply_Tdb=55.0,
        ))
        assert result.ahu_type == AHUType.ECONOMIZER
        assert result.mixed_point is not None


# ── API tests ──


class TestAHUWizardAPI:
    """Test the /api/v1/ahu-wizard endpoint."""

    def test_post_mixed_air(self):
        payload = {
            "ahu_type": "mixed_air",
            "unit_system": "IP",
            "pressure": 14.696,
            "oa_Tdb": 95.0,
            "oa_coincident": 78.0,
            "oa_input_type": "Twb",
            "ra_Tdb": 75.0,
            "ra_RH": 50.0,
            "oa_fraction": 0.3,
            "supply_Tdb": 55.0,
        }
        resp = client.post("/api/v1/ahu-wizard", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["ahu_type"] == "mixed_air"
        assert data["cooling_Qt"] > 0

    def test_post_full_oa(self):
        payload = {
            "ahu_type": "full_oa",
            "unit_system": "IP",
            "pressure": 14.696,
            "oa_Tdb": 95.0,
            "oa_coincident": 78.0,
            "oa_input_type": "Twb",
            "supply_Tdb": 55.0,
        }
        resp = client.post("/api/v1/ahu-wizard", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["ahu_type"] == "full_oa"

    def test_post_validation_error(self):
        payload = {
            "ahu_type": "mixed_air",
            "oa_Tdb": 95.0,
            "oa_coincident": 78.0,
            "supply_Tdb": 55.0,
            # Missing ra_Tdb, ra_RH, oa_fraction
        }
        resp = client.post("/api/v1/ahu-wizard", json=payload)
        assert resp.status_code == 422
