"""
Tests for weather data analysis pipeline: psychrometric calc, clustering,
design point extraction, and the full orchestration pipeline.
"""

import pytest
import psychrolib

from app.engine.tmy_processor import parse_epw_raw
from app.engine.weather_analysis.psychrometric_calc import compute_hourly_states
from app.engine.weather_analysis.clustering import (
    cluster_weather_data,
    label_cluster,
)
from app.engine.weather_analysis.design_extractor import extract_design_conditions


# --- Fixtures ---

# Reuse the EPW fixture from test_tmy.py (8 header lines + 10 data rows)
SAMPLE_EPW = """LOCATION,Sample City,ST,USA,TMY3,724940,35.00,-90.00,-6.0,100.0
DESIGN CONDITIONS,0
TYPICAL/EXTREME PERIODS,0
GROUND TEMPERATURES,0
HOLIDAYS/DAYLIGHT SAVING,No,0,0,0
COMMENTS 1,Sample EPW for testing
COMMENTS 2,Generated for unit tests
DATA PERIODS,1,1,Data,Sunday,1/1,12/31
2020,1,1,1,60,A7A7A7A7*0?9?9?9?9?9?9*0A7A7A7A7*0,-5.0,-10.0,60,101300,0,0,0,0,0,0,0,0,0,0,200,3.0,5,5,10.0,77777,9,999999999,30,0.100,0,88,999
2020,1,1,2,60,A7A7A7A7*0?9?9?9?9?9?9*0A7A7A7A7*0,-4.0,-9.0,62,101300,0,0,0,0,0,0,0,0,0,0,210,2.8,5,5,10.0,77777,9,999999999,30,0.100,0,88,999
2020,1,1,3,60,A7A7A7A7*0?9?9?9?9?9?9*0A7A7A7A7*0,-3.5,-8.5,63,101300,0,0,0,0,0,0,0,0,0,0,220,2.5,4,4,10.0,77777,9,999999999,30,0.100,0,88,999
2020,1,1,4,60,A7A7A7A7*0?9?9?9?9?9?9*0A7A7A7A7*0,-3.0,-8.0,64,101300,0,0,0,0,0,0,0,0,0,0,230,2.3,4,4,10.0,77777,9,999999999,30,0.100,0,88,999
2020,1,1,5,60,A7A7A7A7*0?9?9?9?9?9?9*0A7A7A7A7*0,-2.5,-7.5,65,101300,0,0,0,0,0,0,0,0,0,0,240,2.0,3,3,10.0,77777,9,999999999,30,0.100,0,88,999
2020,1,1,6,60,A7A7A7A7*0?9?9?9?9?9?9*0A7A7A7A7*0,-2.0,-7.0,66,101300,0,0,0,0,0,0,0,0,0,0,250,1.8,3,3,10.0,77777,9,999999999,30,0.100,0,88,999
2020,1,1,7,60,A7A7A7A7*0?9?9?9?9?9?9*0A7A7A7A7*0,-1.5,-6.5,67,101300,0,0,0,0,0,0,0,0,0,0,260,1.5,2,2,10.0,77777,9,999999999,30,0.100,0,88,999
2020,7,1,12,60,A7A7A7A7*0?9?9?9?9?9?9*0A7A7A7A7*0,32.0,22.0,55,101000,0,0,0,0,0,0,0,0,0,0,180,4.0,3,3,10.0,77777,9,999999999,30,0.100,0,88,999
2020,7,1,13,60,A7A7A7A7*0?9?9?9?9?9?9*0A7A7A7A7*0,33.5,21.5,48,101000,0,0,0,0,0,0,0,0,0,0,190,3.5,2,2,10.0,77777,9,999999999,30,0.100,0,88,999
2020,7,1,14,60,A7A7A7A7*0?9?9?9?9?9?9*0A7A7A7A7*0,34.0,20.0,42,101000,0,0,0,0,0,0,0,0,0,0,200,3.0,1,1,10.0,77777,9,999999999,30,0.100,0,88,999
"""


def _approx(val, rel=0.01, abs_tol=0.1):
    """Approximate comparison with 1% relative or 0.1 absolute tolerance."""
    return pytest.approx(val, rel=rel, abs=abs_tol)


# --- parse_epw_raw tests ---

class TestParseEPWRaw:
    def test_returns_records(self):
        raw = parse_epw_raw(SAMPLE_EPW)
        assert len(raw["records"]) == 10

    def test_location_metadata(self):
        raw = parse_epw_raw(SAMPLE_EPW)
        loc = raw["location"]
        assert loc["city"] == "Sample City"
        assert loc["state"] == "ST"
        assert loc["country"] == "USA"
        assert loc["latitude"] == _approx(35.0)
        assert loc["longitude"] == _approx(-90.0)
        assert loc["timezone"] == _approx(-6.0)
        assert loc["elevation"] == _approx(100.0)

    def test_location_name(self):
        raw = parse_epw_raw(SAMPLE_EPW)
        assert raw["location_name"] == "Sample City, ST, USA"

    def test_record_fields(self):
        raw = parse_epw_raw(SAMPLE_EPW)
        rec = raw["records"][0]
        assert rec["tdb_c"] == _approx(-5.0)
        assert rec["tdp_c"] == _approx(-10.0)
        assert rec["pressure_pa"] == _approx(101300.0)
        assert rec["month"] == 1
        assert rec["day"] == 1
        assert rec["hour"] == 1

    def test_hot_record_values(self):
        raw = parse_epw_raw(SAMPLE_EPW)
        # Last record: 34.0°C, 20.0°C dp
        rec = raw["records"][-1]
        assert rec["tdb_c"] == _approx(34.0)
        assert rec["tdp_c"] == _approx(20.0)
        assert rec["month"] == 7

    def test_empty_file_raises(self):
        with pytest.raises(ValueError, match="too short"):
            parse_epw_raw("short")


# --- psychrometric_calc tests ---

class TestComputeHourlyStates:
    def test_computes_all_records(self):
        raw = parse_epw_raw(SAMPLE_EPW)
        states = compute_hourly_states(raw["records"])
        assert len(states) == 10

    def test_known_condition(self):
        """Verify psychrometric properties at 35°C DB, 20°C DP, 101325 Pa."""
        records = [{
            "tdb_c": 35.0,
            "tdp_c": 20.0,
            "pressure_pa": 101325.0,
            "month": 7,
            "day": 15,
            "hour": 14,
        }]
        states = compute_hourly_states(records)
        assert len(states) == 1
        s = states[0]

        # Verify against psychrolib reference
        psychrolib.SetUnitSystem(psychrolib.SI)
        expected_w = psychrolib.GetHumRatioFromTDewPoint(20.0, 101325.0)
        expected_twb = psychrolib.GetTWetBulbFromTDewPoint(35.0, 20.0, 101325.0)
        expected_rh = psychrolib.GetRelHumFromTDewPoint(35.0, 20.0)
        expected_h = psychrolib.GetMoistAirEnthalpy(35.0, expected_w)
        expected_v = psychrolib.GetMoistAirVolume(35.0, expected_w, 101325.0)

        assert s.dry_bulb_c == _approx(35.0)
        assert s.dewpoint_c == _approx(20.0)
        assert s.humidity_ratio == _approx(expected_w, rel=0.001)
        assert s.wet_bulb_c == _approx(expected_twb, rel=0.01)
        assert s.relative_humidity == _approx(expected_rh, rel=0.01)
        assert s.enthalpy_j_per_kg == _approx(expected_h, rel=0.01)
        assert s.specific_volume == _approx(expected_v, rel=0.01)

    def test_cold_condition(self):
        """Verify at 0°C DB, -5°C DP."""
        records = [{
            "tdb_c": 0.0,
            "tdp_c": -5.0,
            "pressure_pa": 101325.0,
            "month": 1,
            "day": 1,
            "hour": 1,
        }]
        states = compute_hourly_states(records)
        assert len(states) == 1
        s = states[0]

        assert s.dry_bulb_c == _approx(0.0)
        assert s.humidity_ratio > 0
        assert 0.0 < s.relative_humidity < 1.0

    def test_skips_corrupt_records(self):
        """Records with invalid data should be skipped, not crash."""
        records = [
            {"tdb_c": 25.0, "tdp_c": 15.0, "pressure_pa": 101325.0,
             "month": 6, "day": 1, "hour": 1},
            {"tdb_c": "bad", "tdp_c": 15.0, "pressure_pa": 101325.0,
             "month": 6, "day": 1, "hour": 2},
            {"tdb_c": 30.0, "tdp_c": 20.0, "pressure_pa": 101325.0,
             "month": 6, "day": 1, "hour": 3},
        ]
        states = compute_hourly_states(records)
        assert len(states) == 2

    def test_dewpoint_clamped_to_drybulb(self):
        """If dewpoint > dry-bulb (corrupt data), clamp it."""
        records = [{
            "tdb_c": 20.0,
            "tdp_c": 25.0,  # dewpoint > dry-bulb, physically impossible
            "pressure_pa": 101325.0,
            "month": 6,
            "day": 1,
            "hour": 1,
        }]
        states = compute_hourly_states(records)
        assert len(states) == 1
        # Dewpoint should have been clamped to dry-bulb
        assert states[0].dewpoint_c == _approx(20.0)
        assert states[0].relative_humidity == _approx(1.0, rel=0.01)


# --- clustering tests ---

class TestClusterWeatherData:
    def _make_states(self, data):
        """Helper: create HourlyPsychroState objects from (tdb_c, w) pairs."""
        psychrolib.SetUnitSystem(psychrolib.SI)
        from app.models.weather_analysis import HourlyPsychroState
        states = []
        for tdb_c, w in data:
            h = psychrolib.GetMoistAirEnthalpy(tdb_c, w)
            states.append(HourlyPsychroState(
                month=1, day=1, hour=1,
                dry_bulb_c=tdb_c,
                wet_bulb_c=tdb_c,  # approximate
                dewpoint_c=tdb_c - 5,  # approximate
                humidity_ratio=w,
                relative_humidity=0.5,
                enthalpy_j_per_kg=h,
                specific_volume=0.85,
                pressure_pa=101325.0,
            ))
        return states

    def test_two_blobs_separated(self):
        """Two well-separated groups should land in different clusters."""
        import numpy as np
        rng = np.random.RandomState(42)
        # Group A: cold/dry (around 0°C, W=0.002)
        group_a = [(rng.normal(0, 1), rng.normal(0.002, 0.0005))
                    for _ in range(50)]
        # Group B: hot/humid (around 35°C, W=0.020)
        group_b = [(rng.normal(35, 1), rng.normal(0.020, 0.001))
                    for _ in range(50)]
        states = self._make_states(group_a + group_b)

        result = cluster_weather_data(states, n_clusters=2)
        labels = result["labels"]

        # All group A points should share one label
        labels_a = set(labels[:50])
        labels_b = set(labels[50:])
        assert len(labels_a) == 1
        assert len(labels_b) == 1
        assert labels_a != labels_b

    def test_hour_counts_sum(self):
        """Hour counts across all clusters should sum to total states."""
        raw = parse_epw_raw(SAMPLE_EPW)
        states = compute_hourly_states(raw["records"])

        result = cluster_weather_data(states, n_clusters=2)
        total = sum(ci["hour_count"] for ci in result["cluster_infos"])
        assert total == len(states)

    def test_worst_case_is_max_enthalpy_per_cluster(self):
        """Worst-case point should have the highest enthalpy in its cluster."""
        raw = parse_epw_raw(SAMPLE_EPW)
        states = compute_hourly_states(raw["records"])

        result = cluster_weather_data(states, n_clusters=2)

        for ci in result["cluster_infos"]:
            cid = ci["cluster_id"]
            cluster_states = [
                states[i] for i, lbl in enumerate(result["labels"])
                if lbl == cid
            ]
            max_h = max(s.enthalpy_j_per_kg for s in cluster_states)
            assert ci["worst_case_state"].enthalpy_j_per_kg == _approx(max_h, rel=0.001)

    def test_cluster_infos_have_labels(self):
        """Each cluster should have a descriptive label."""
        raw = parse_epw_raw(SAMPLE_EPW)
        states = compute_hourly_states(raw["records"])

        result = cluster_weather_data(states, n_clusters=2)

        for ci in result["cluster_infos"]:
            assert isinstance(ci["label"], str)
            assert len(ci["label"]) > 0

    def test_n_clusters_respected(self):
        """Should produce the requested number of clusters."""
        raw = parse_epw_raw(SAMPLE_EPW)
        states = compute_hourly_states(raw["records"])

        for k in [2, 3]:
            result = cluster_weather_data(states, n_clusters=k)
            assert len(result["cluster_infos"]) == k
            assert len(set(result["labels"])) == k


class TestLabelCluster:
    def test_hot_humid(self):
        assert label_cluster(35.0, 0.80) == "Hot Humid"

    def test_warm_moderate(self):
        assert label_cluster(26.0, 0.50) == "Warm Moderate"

    def test_cold_dry(self):
        assert label_cluster(-5.0, 0.20) == "Cold Dry"

    def test_mild_humid(self):
        assert label_cluster(18.0, 0.70) == "Mild Humid"

    def test_cool_moderate(self):
        assert label_cluster(10.0, 0.45) == "Cool Moderate"


# --- design_extractor tests ---

class TestExtractDesignConditions:
    def test_full_pipeline_ip(self):
        result = extract_design_conditions(SAMPLE_EPW, n_clusters=2, unit_system="IP")

        # Should have 3 extremes + 2 cluster worst-case = 5 design points
        assert len(result.design_points) == 5
        assert result.total_hours == 10

    def test_full_pipeline_si(self):
        result = extract_design_conditions(SAMPLE_EPW, n_clusters=2, unit_system="SI")

        assert len(result.design_points) == 5
        assert result.unit_system == "SI"

    def test_location_populated(self):
        result = extract_design_conditions(SAMPLE_EPW, n_clusters=2)

        assert result.location.city == "Sample City"
        assert result.location.state == "ST"
        assert result.location.country == "USA"
        assert result.location.latitude == _approx(35.0)

    def test_extreme_points_types(self):
        result = extract_design_conditions(SAMPLE_EPW, n_clusters=2)

        extremes = [dp for dp in result.design_points if dp.point_type == "extreme"]
        assert len(extremes) == 3

        labels = {dp.label for dp in extremes}
        assert "Peak Cooling" in labels
        assert "Peak Heating" in labels
        assert "Peak Dehumidification" in labels

    def test_peak_cooling_has_max_enthalpy(self):
        """Peak cooling should be the hour with highest enthalpy."""
        result = extract_design_conditions(SAMPLE_EPW, n_clusters=2, unit_system="IP")

        peak_cooling = next(
            dp for dp in result.design_points if dp.label == "Peak Cooling"
        )
        other_enthalpies = [
            dp.enthalpy for dp in result.design_points if dp.label != "Peak Cooling"
        ]
        assert all(peak_cooling.enthalpy >= h for h in other_enthalpies)

    def test_peak_heating_has_min_drybulb(self):
        """Peak heating should be the hour with lowest dry-bulb."""
        result = extract_design_conditions(SAMPLE_EPW, n_clusters=2, unit_system="IP")

        peak_heating = next(
            dp for dp in result.design_points if dp.label == "Peak Heating"
        )
        other_dbs = [
            dp.dry_bulb for dp in result.design_points if dp.label != "Peak Heating"
        ]
        assert all(peak_heating.dry_bulb <= db for db in other_dbs)

    def test_cluster_worst_case_points(self):
        """Cluster worst-case points should have cluster metadata."""
        result = extract_design_conditions(SAMPLE_EPW, n_clusters=2)

        cluster_points = [
            dp for dp in result.design_points
            if dp.point_type == "cluster_worst_case"
        ]
        assert len(cluster_points) == 2

        for dp in cluster_points:
            assert dp.cluster_id is not None
            assert dp.hours_in_cluster is not None
            assert dp.hours_in_cluster > 0

    def test_cluster_summary(self):
        result = extract_design_conditions(SAMPLE_EPW, n_clusters=2)

        assert len(result.cluster_summary) == 2
        total_hours = sum(cs.hour_count for cs in result.cluster_summary)
        assert total_hours == 10

        for cs in result.cluster_summary:
            assert isinstance(cs.label, str)
            assert cs.fraction_of_year > 0
            assert cs.fraction_of_year <= 1.0

    def test_chart_data(self):
        result = extract_design_conditions(SAMPLE_EPW, n_clusters=2)

        assert len(result.chart_data) == 10
        for pt in result.chart_data:
            assert pt.cluster_id in [0, 1]
            assert isinstance(pt.dry_bulb, float)
            assert isinstance(pt.humidity_ratio, float)

    def test_ip_units_conversion(self):
        """In IP mode, temperatures should be in °F range."""
        result = extract_design_conditions(SAMPLE_EPW, n_clusters=2, unit_system="IP")

        peak_cooling = next(
            dp for dp in result.design_points if dp.label == "Peak Cooling"
        )
        # 34°C = 93.2°F
        assert peak_cooling.dry_bulb > 80  # should be in °F

    def test_si_units(self):
        """In SI mode, temperatures should stay in °C range."""
        result = extract_design_conditions(SAMPLE_EPW, n_clusters=2, unit_system="SI")

        peak_cooling = next(
            dp for dp in result.design_points if dp.label == "Peak Cooling"
        )
        # 34°C should stay as °C
        assert peak_cooling.dry_bulb < 50  # should be in °C

    def test_invalid_file_raises(self):
        with pytest.raises(ValueError):
            extract_design_conditions("not an epw file", n_clusters=2)

    def test_different_cluster_counts(self):
        for k in [2, 3]:
            result = extract_design_conditions(SAMPLE_EPW, n_clusters=k)
            cluster_points = [
                dp for dp in result.design_points
                if dp.point_type == "cluster_worst_case"
            ]
            assert len(cluster_points) == k
            assert len(result.cluster_summary) == k
