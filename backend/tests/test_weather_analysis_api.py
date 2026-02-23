"""
API-level tests for weather analysis endpoint (POST /api/v1/weather/analyze).
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

# Reuse the same EPW fixture from test_tmy.py / test_weather_analysis.py
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


class TestWeatherAnalyzeEndpoint:
    def test_upload_success(self):
        resp = client.post(
            "/api/v1/weather/analyze?unit_system=IP&n_clusters=2",
            files={"file": ("test.epw", SAMPLE_EPW.encode(), "application/octet-stream")},
        )
        assert resp.status_code == 200
        data = resp.json()

        # Top-level structure
        assert "location" in data
        assert "design_points" in data
        assert "cluster_summary" in data
        assert "chart_data" in data
        assert data["total_hours"] == 10
        assert data["unit_system"] == "IP"

    def test_design_points_structure(self):
        resp = client.post(
            "/api/v1/weather/analyze?unit_system=IP&n_clusters=2",
            files={"file": ("test.epw", SAMPLE_EPW.encode(), "application/octet-stream")},
        )
        data = resp.json()

        # 3 extremes + 2 cluster worst-case = 5
        assert len(data["design_points"]) == 5

        for dp in data["design_points"]:
            assert "label" in dp
            assert "point_type" in dp
            assert "dry_bulb" in dp
            assert "wet_bulb" in dp
            assert "dewpoint" in dp
            assert "humidity_ratio" in dp
            assert "enthalpy" in dp
            assert "relative_humidity" in dp
            assert "specific_volume" in dp
            assert "month" in dp
            assert "day" in dp
            assert "hour" in dp

    def test_extreme_points_present(self):
        resp = client.post(
            "/api/v1/weather/analyze?n_clusters=2",
            files={"file": ("test.epw", SAMPLE_EPW.encode(), "application/octet-stream")},
        )
        data = resp.json()

        labels = [dp["label"] for dp in data["design_points"]]
        assert "Peak Cooling" in labels
        assert "Peak Heating" in labels
        assert "Peak Dehumidification" in labels

    def test_cluster_summary_structure(self):
        resp = client.post(
            "/api/v1/weather/analyze?n_clusters=2",
            files={"file": ("test.epw", SAMPLE_EPW.encode(), "application/octet-stream")},
        )
        data = resp.json()

        assert len(data["cluster_summary"]) == 2
        total = sum(cs["hour_count"] for cs in data["cluster_summary"])
        assert total == 10

        for cs in data["cluster_summary"]:
            assert "cluster_id" in cs
            assert "label" in cs
            assert "hour_count" in cs
            assert "fraction_of_year" in cs
            assert "centroid_dry_bulb" in cs
            assert "centroid_humidity_ratio" in cs

    def test_chart_data_structure(self):
        resp = client.post(
            "/api/v1/weather/analyze?n_clusters=2",
            files={"file": ("test.epw", SAMPLE_EPW.encode(), "application/octet-stream")},
        )
        data = resp.json()

        assert len(data["chart_data"]) == 10
        for pt in data["chart_data"]:
            assert "dry_bulb" in pt
            assert "humidity_ratio" in pt
            assert "cluster_id" in pt

    def test_location_populated(self):
        resp = client.post(
            "/api/v1/weather/analyze?n_clusters=2",
            files={"file": ("test.epw", SAMPLE_EPW.encode(), "application/octet-stream")},
        )
        data = resp.json()

        loc = data["location"]
        assert loc["city"] == "Sample City"
        assert loc["state"] == "ST"
        assert loc["country"] == "USA"
        assert abs(loc["latitude"] - 35.0) < 0.1

    def test_n_clusters_3(self):
        resp = client.post(
            "/api/v1/weather/analyze?n_clusters=3",
            files={"file": ("test.epw", SAMPLE_EPW.encode(), "application/octet-stream")},
        )
        data = resp.json()

        cluster_points = [
            dp for dp in data["design_points"]
            if dp["point_type"] == "cluster_worst_case"
        ]
        assert len(cluster_points) == 3
        assert len(data["cluster_summary"]) == 3

    def test_si_unit_system(self):
        resp = client.post(
            "/api/v1/weather/analyze?unit_system=SI&n_clusters=2",
            files={"file": ("test.epw", SAMPLE_EPW.encode(), "application/octet-stream")},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["unit_system"] == "SI"

        # In SI, the hottest point (34°C) should remain in °C range
        peak_cooling = next(
            dp for dp in data["design_points"] if dp["label"] == "Peak Cooling"
        )
        assert peak_cooling["dry_bulb"] < 50  # °C range

    def test_wrong_filetype_rejected(self):
        resp = client.post(
            "/api/v1/weather/analyze?n_clusters=2",
            files={"file": ("test.csv", b"some,csv,data\n", "text/csv")},
        )
        assert resp.status_code == 400
        assert "epw" in resp.json()["detail"].lower()

    def test_txt_file_rejected(self):
        resp = client.post(
            "/api/v1/weather/analyze",
            files={"file": ("readme.txt", b"not weather data", "text/plain")},
        )
        assert resp.status_code == 400

    def test_invalid_epw_content(self):
        resp = client.post(
            "/api/v1/weather/analyze?n_clusters=2",
            files={"file": ("bad.epw", b"this is not epw data\n", "application/octet-stream")},
        )
        assert resp.status_code == 422

    def test_existing_tmy_endpoint_unaffected(self):
        """Verify the original TMY upload endpoint still works."""
        resp = client.post(
            "/api/v1/tmy/upload?unit_system=IP&pressure=14.696",
            files={"file": ("test.epw", SAMPLE_EPW.encode(), "application/octet-stream")},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_hours"] == 10
        assert "scatter_points" in data
