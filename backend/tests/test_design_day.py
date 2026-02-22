"""
Tests for ASHRAE design day conditions engine and API.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.engine.design_day import (
    load_locations,
    search_locations,
    resolve_design_conditions,
)

client = TestClient(app)


# ─── Engine tests ───


class TestLoadLocations:
    def test_loads_nonempty(self):
        locs = load_locations()
        assert len(locs) > 0

    def test_location_has_required_fields(self):
        locs = load_locations()
        for loc in locs:
            assert "name" in loc
            assert "state" in loc
            assert "country" in loc
            assert "elevation_ft" in loc
            assert "conditions" in loc
            assert "climate_zone" in loc


class TestSearchLocations:
    def test_search_by_city_name(self):
        results = search_locations("Phoenix")
        assert len(results) >= 1
        assert results[0]["name"] == "Phoenix"

    def test_search_case_insensitive(self):
        results = search_locations("phoenix")
        assert len(results) >= 1
        assert results[0]["name"] == "Phoenix"

    def test_search_partial_match(self):
        results = search_locations("New")
        names = [r["name"] for r in results]
        assert "New York City" in names or "New Orleans" in names

    def test_search_by_state(self):
        results = search_locations("TX")
        assert len(results) >= 1
        assert all(r["state"] == "TX" for r in results)

    def test_search_empty_returns_all(self):
        results = search_locations("", limit=5)
        assert len(results) == 5

    def test_search_limit(self):
        results = search_locations("", limit=3)
        assert len(results) == 3

    def test_search_no_match(self):
        results = search_locations("Zzzznotacity")
        assert len(results) == 0


class TestResolveDesignConditions:
    def test_resolve_all_conditions_ip(self):
        result = resolve_design_conditions(
            location_name="Phoenix",
            location_state="AZ",
            condition_labels=[],
            unit_system="IP",
        )
        assert result["location"]["name"] == "Phoenix"
        assert result["unit_system"] == "IP"
        assert len(result["points"]) > 0
        assert result["pressure_used"] > 0

    def test_resolve_specific_condition(self):
        result = resolve_design_conditions(
            location_name="Phoenix",
            location_state="AZ",
            condition_labels=["0.4% Cooling DB / MCWB"],
            unit_system="IP",
        )
        assert len(result["points"]) == 1
        pt = result["points"][0]
        assert pt["condition_label"] == "0.4% Cooling DB / MCWB"
        assert pt["category"] == "cooling_db"

    def test_resolved_point_has_valid_properties(self):
        result = resolve_design_conditions(
            location_name="Miami",
            location_state="FL",
            condition_labels=["0.4% Cooling DB / MCWB"],
            unit_system="IP",
        )
        pt = result["points"][0]
        assert 50 < pt["Tdb"] < 120  # reasonable F range
        assert 0 < pt["RH"] < 100
        assert pt["W"] > 0
        assert pt["W_display"] > 0
        assert pt["h"] > 0
        assert pt["v"] > 0

    def test_resolve_si_units(self):
        result = resolve_design_conditions(
            location_name="Chicago",
            location_state="IL",
            condition_labels=[],
            unit_system="SI",
        )
        assert result["unit_system"] == "SI"
        # SI Tdb for Chicago summer should be roughly 30-35°C
        cooling_pts = [p for p in result["points"] if p["category"] == "cooling_db"]
        assert len(cooling_pts) > 0

    def test_resolve_with_pressure_override(self):
        result = resolve_design_conditions(
            location_name="Denver",
            location_state="CO",
            condition_labels=[],
            unit_system="IP",
            pressure_override=14.696,
        )
        assert result["pressure_used"] == 14.696

    def test_resolve_heating_conditions(self):
        result = resolve_design_conditions(
            location_name="Minneapolis",
            location_state="MN",
            condition_labels=["99.6% Heating DB"],
            unit_system="IP",
        )
        assert len(result["points"]) == 1
        pt = result["points"][0]
        assert pt["category"] == "heating"
        assert pt["Tdb"] < 0  # Minneapolis heating is below 0°F

    def test_resolve_cooling_wb_conditions(self):
        result = resolve_design_conditions(
            location_name="Houston",
            location_state="TX",
            condition_labels=["0.4% Cooling WB / MCDB"],
            unit_system="IP",
        )
        assert len(result["points"]) == 1
        pt = result["points"][0]
        assert pt["category"] == "cooling_wb"

    def test_location_not_found(self):
        with pytest.raises(ValueError, match="not found"):
            resolve_design_conditions(
                location_name="Nonexistent City",
                location_state="",
                condition_labels=[],
                unit_system="IP",
            )

    def test_pressure_from_elevation_denver(self):
        """Denver is at 5331 ft, pressure should be lower than sea level."""
        result = resolve_design_conditions(
            location_name="Denver",
            location_state="CO",
            condition_labels=["0.4% Cooling DB / MCWB"],
            unit_system="IP",
        )
        assert result["pressure_used"] < 14.696  # less than sea level


# ─── API tests ───


class TestDesignDayAPI:
    def test_search_endpoint(self):
        resp = client.get("/api/v1/design-days/search?q=Phoenix")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1
        assert data[0]["name"] == "Phoenix"

    def test_search_endpoint_empty(self):
        resp = client.get("/api/v1/design-days/search?q=&limit=5")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 5

    def test_resolve_endpoint(self):
        resp = client.post("/api/v1/design-days/resolve", json={
            "location_name": "Miami",
            "location_state": "FL",
            "condition_labels": [],
            "unit_system": "IP",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["location"]["name"] == "Miami"
        assert len(data["points"]) > 0

    def test_resolve_endpoint_not_found(self):
        resp = client.post("/api/v1/design-days/resolve", json={
            "location_name": "Nonexistent",
            "condition_labels": [],
            "unit_system": "IP",
        })
        assert resp.status_code == 404
