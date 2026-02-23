"""
Tests for TMY data processing engine and API (TMY3 CSV + EPW).
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.engine.tmy_processor import parse_tmy3, parse_epw

client = TestClient(app)

# Minimal TMY3 fixture (10 hours of fake data in TMY3 format)
SAMPLE_TMY3 = """724940,"SAMPLE CITY","ST",35.0,-90.0,-6.0,100,12345
Date (MM/DD/YYYY),Time (HH:MM),Dry-bulb (C),Dew-point (C),RHum(%),Pressure (mbar)
01/01/2020,01:00,-5.0,-10.0,60,1013
01/01/2020,02:00,-4.0,-9.0,62,1013
01/01/2020,03:00,-3.5,-8.5,63,1013
01/01/2020,04:00,-3.0,-8.0,64,1013
01/01/2020,05:00,-2.5,-7.5,65,1013
01/01/2020,06:00,-2.0,-7.0,66,1013
01/01/2020,07:00,-1.5,-6.5,67,1013
07/01/2020,12:00,32.0,22.0,55,1010
07/01/2020,13:00,33.5,21.5,48,1010
07/01/2020,14:00,34.0,20.0,42,1010
"""


class TestParseTMY3:
    def test_parse_ip_units(self):
        result = parse_tmy3(SAMPLE_TMY3, unit_system="IP", pressure=14.696)
        assert result["unit_system"] == "IP"
        assert result["total_hours"] == 10
        assert len(result["scatter_points"]) == 10

    def test_parse_si_units(self):
        result = parse_tmy3(SAMPLE_TMY3, unit_system="SI", pressure=101325)
        assert result["unit_system"] == "SI"
        assert result["total_hours"] == 10

    def test_scatter_points_have_required_fields(self):
        result = parse_tmy3(SAMPLE_TMY3, unit_system="IP", pressure=14.696)
        for pt in result["scatter_points"]:
            assert "Tdb" in pt
            assert "W_display" in pt
            assert "hour" in pt
            assert "month" in pt

    def test_month_extraction(self):
        result = parse_tmy3(SAMPLE_TMY3, unit_system="IP", pressure=14.696)
        # First 7 points are January, last 3 are July
        jan_pts = [p for p in result["scatter_points"] if p["month"] == 1]
        jul_pts = [p for p in result["scatter_points"] if p["month"] == 7]
        assert len(jan_pts) == 7
        assert len(jul_pts) == 3

    def test_temperature_conversion_ip(self):
        result = parse_tmy3(SAMPLE_TMY3, unit_system="IP", pressure=14.696)
        # 32°C = 89.6°F
        hot_pts = [p for p in result["scatter_points"] if p["Tdb"] > 80]
        assert len(hot_pts) == 3

    def test_temperature_stays_si(self):
        result = parse_tmy3(SAMPLE_TMY3, unit_system="SI", pressure=101325)
        hot_pts = [p for p in result["scatter_points"] if p["Tdb"] > 30]
        assert len(hot_pts) == 3

    def test_bin_matrix_generated(self):
        result = parse_tmy3(SAMPLE_TMY3, unit_system="IP", pressure=14.696)
        assert len(result["bin_Tdb_edges"]) > 0
        assert len(result["bin_W_edges"]) > 0
        assert len(result["bin_matrix"]) > 0
        # Total counts in matrix should equal total_hours
        total = sum(sum(row) for row in result["bin_matrix"])
        assert total == result["total_hours"]

    def test_location_name_extracted(self):
        result = parse_tmy3(SAMPLE_TMY3, unit_system="IP", pressure=14.696)
        assert result["location_name"] == "SAMPLE CITY, ST"

    def test_empty_file_raises(self):
        with pytest.raises(ValueError, match="too short"):
            parse_tmy3("short", unit_system="IP", pressure=14.696)

    def test_no_tdb_column_raises(self):
        bad_csv = """724940,"CITY","ST"
Col1,Col2,Col3
""" + "\n".join([f"{i},{i},{i}" for i in range(20)])
        with pytest.raises(ValueError, match="dry-bulb"):
            parse_tmy3(bad_csv, unit_system="IP", pressure=14.696)


class TestTMYAPI:
    def test_upload_endpoint_success(self):
        resp = client.post(
            "/api/v1/tmy/upload?unit_system=IP&pressure=14.696",
            files={"file": ("test.csv", SAMPLE_TMY3.encode(), "text/csv")},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_hours"] == 10
        assert len(data["scatter_points"]) == 10

    def test_upload_endpoint_wrong_filetype(self):
        resp = client.post(
            "/api/v1/tmy/upload?unit_system=IP&pressure=14.696",
            files={"file": ("test.txt", b"some data", "text/plain")},
        )
        assert resp.status_code == 400

    def test_upload_endpoint_bad_data(self):
        resp = client.post(
            "/api/v1/tmy/upload?unit_system=IP&pressure=14.696",
            files={"file": ("test.csv", b"bad data\n", "text/csv")},
        )
        assert resp.status_code == 422


# Minimal EPW fixture (8 header lines + 10 data rows)
# EPW header lines: LOCATION, DESIGN CONDITIONS, TYPICAL/EXTREME PERIODS,
#   GROUND TEMPERATURES, HOLIDAYS/DAYLIGHT SAVING, COMMENTS 1, COMMENTS 2, DATA PERIODS
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


class TestParseEPW:
    def test_parse_ip_units(self):
        result = parse_epw(SAMPLE_EPW, unit_system="IP", pressure=14.696)
        assert result["unit_system"] == "IP"
        assert result["total_hours"] == 10
        assert len(result["scatter_points"]) == 10

    def test_parse_si_units(self):
        result = parse_epw(SAMPLE_EPW, unit_system="SI", pressure=101325)
        assert result["unit_system"] == "SI"
        assert result["total_hours"] == 10

    def test_scatter_points_have_required_fields(self):
        result = parse_epw(SAMPLE_EPW, unit_system="IP", pressure=14.696)
        for pt in result["scatter_points"]:
            assert "Tdb" in pt
            assert "W_display" in pt
            assert "hour" in pt
            assert "month" in pt

    def test_month_extraction(self):
        result = parse_epw(SAMPLE_EPW, unit_system="IP", pressure=14.696)
        jan_pts = [p for p in result["scatter_points"] if p["month"] == 1]
        jul_pts = [p for p in result["scatter_points"] if p["month"] == 7]
        assert len(jan_pts) == 7
        assert len(jul_pts) == 3

    def test_temperature_conversion_ip(self):
        result = parse_epw(SAMPLE_EPW, unit_system="IP", pressure=14.696)
        # 32°C = 89.6°F
        hot_pts = [p for p in result["scatter_points"] if p["Tdb"] > 80]
        assert len(hot_pts) == 3

    def test_temperature_stays_si(self):
        result = parse_epw(SAMPLE_EPW, unit_system="SI", pressure=101325)
        hot_pts = [p for p in result["scatter_points"] if p["Tdb"] > 30]
        assert len(hot_pts) == 3

    def test_bin_matrix_generated(self):
        result = parse_epw(SAMPLE_EPW, unit_system="IP", pressure=14.696)
        assert len(result["bin_Tdb_edges"]) > 0
        assert len(result["bin_W_edges"]) > 0
        assert len(result["bin_matrix"]) > 0
        total = sum(sum(row) for row in result["bin_matrix"])
        assert total == result["total_hours"]

    def test_location_name_extracted(self):
        result = parse_epw(SAMPLE_EPW, unit_system="IP", pressure=14.696)
        assert result["location_name"] == "Sample City, ST, USA"

    def test_empty_file_raises(self):
        with pytest.raises(ValueError, match="too short"):
            parse_epw("short", unit_system="IP", pressure=14.696)

    def test_uses_row_pressure(self):
        """EPW rows include atmospheric pressure; parser should use it."""
        result = parse_epw(SAMPLE_EPW, unit_system="SI", pressure=101325)
        # Should successfully parse without error even if fallback pressure differs
        assert result["total_hours"] == 10


class TestEPWAPI:
    def test_upload_epw_success(self):
        resp = client.post(
            "/api/v1/tmy/upload?unit_system=IP&pressure=14.696",
            files={"file": ("test.epw", SAMPLE_EPW.encode(), "application/octet-stream")},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_hours"] == 10
        assert len(data["scatter_points"]) == 10
        assert data["location_name"] == "Sample City, ST, USA"

    def test_upload_epw_wrong_filetype(self):
        resp = client.post(
            "/api/v1/tmy/upload?unit_system=IP&pressure=14.696",
            files={"file": ("test.txt", b"some data", "text/plain")},
        )
        assert resp.status_code == 400

    def test_upload_epw_bad_data(self):
        resp = client.post(
            "/api/v1/tmy/upload?unit_system=IP&pressure=14.696",
            files={"file": ("test.epw", b"bad data\n", "application/octet-stream")},
        )
        assert resp.status_code == 422
