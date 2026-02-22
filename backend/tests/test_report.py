"""
Tests for the PDF report generator engine and API route.
"""

import base64
import struct
import zlib

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.engine.report_generator import generate_report
from app.models.report import ReportInput


client = TestClient(app)


def _minimal_png_b64() -> str:
    """Create a minimal valid 1x1 PNG image encoded as base64."""
    # Minimal 1x1 white PNG
    def _chunk(chunk_type: bytes, data: bytes) -> bytes:
        c = chunk_type + data
        crc = struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)
        return struct.pack(">I", len(data)) + c + crc

    signature = b"\x89PNG\r\n\x1a\n"
    ihdr_data = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)  # 1x1 RGB
    ihdr = _chunk(b"IHDR", ihdr_data)
    raw_row = b"\x00\xff\xff\xff"  # filter byte + RGB white pixel
    idat_data = zlib.compress(raw_row)
    idat = _chunk(b"IDAT", idat_data)
    iend = _chunk(b"IEND", b"")
    png_bytes = signature + ihdr + idat + iend
    return base64.b64encode(png_bytes).decode()


def _sample_state_point() -> dict:
    return {
        "label": "Point 1",
        "unit_system": "IP",
        "pressure": 14.696,
        "input_pair": ["Tdb", "RH"],
        "input_values": [75.0, 50.0],
        "Tdb": 75.0,
        "Twb": 62.5,
        "Tdp": 55.1,
        "RH": 50.0,
        "W": 0.009297,
        "W_display": 65.08,
        "h": 28.11,
        "v": 13.68,
        "Pv": 0.2148,
        "Ps": 0.4298,
        "mu": 0.5,
    }


def _sample_process() -> dict:
    return {
        "process_type": "sensible_heating",
        "unit_system": "IP",
        "pressure": 14.696,
        "start_point": _sample_state_point(),
        "end_point": {**_sample_state_point(), "Tdb": 95.0, "label": "End"},
        "path_points": [],
        "metadata": {
            "Qs": 4.88,
            "Ql": 0.0,
            "Qt": 4.88,
            "SHR": 1.0,
            "delta_T": 20.0,
        },
        "warnings": [],
    }


def _sample_coil() -> dict:
    return {
        "unit_system": "IP",
        "pressure": 14.696,
        "mode": "forward",
        "entering": _sample_state_point(),
        "leaving": {**_sample_state_point(), "Tdb": 55.0, "label": "Leaving"},
        "adp": {**_sample_state_point(), "Tdb": 48.0, "label": "ADP"},
        "bypass_factor": 0.15,
        "contact_factor": 0.85,
        "Qs": 4.88,
        "Ql": 2.5,
        "Qt": 7.38,
        "SHR": 0.66,
        "load_unit": "BTU/lb",
        "gpm": 12.5,
        "path_points": [],
        "warnings": [],
    }


# ── Engine tests ──


class TestReportGenerator:
    """Test the report generator engine directly."""

    def test_minimal_report(self):
        """Generate a report with just a chart image and one state point."""
        inp = ReportInput(
            title="Test Report",
            chart_image_base64=_minimal_png_b64(),
            state_points=[_sample_state_point()],
            include_sections=["chart", "state_points"],
        )
        pdf_bytes = generate_report(inp)

        # Verify it's a valid PDF (starts with %PDF)
        assert pdf_bytes[:5] == b"%PDF-"
        assert len(pdf_bytes) > 100

    def test_full_report(self):
        """Generate a report with all sections."""
        inp = ReportInput(
            title="Full Test Report",
            chart_image_base64=_minimal_png_b64(),
            state_points=[_sample_state_point(), {**_sample_state_point(), "label": "Point 2"}],
            processes=[_sample_process()],
            coil_result=_sample_coil(),
            shr_lines=[{
                "room_point": _sample_state_point(),
                "shr": 0.75,
                "slope_dW_dTdb": -0.001,
                "line_points": [],
                "adp": _sample_state_point(),
                "adp_Tdb": 50.0,
                "warnings": [],
            }],
            gshr_result={
                "room_shr": 0.75,
                "gshr": 0.65,
                "eshr": 0.60,
            },
            notes="These are test notes for the report.\nWith multiple lines.",
            include_sections=["chart", "state_points", "processes", "coil", "shr", "notes"],
        )
        pdf_bytes = generate_report(inp)

        assert pdf_bytes[:5] == b"%PDF-"
        assert len(pdf_bytes) > 500

    def test_si_units(self):
        """Generate a report with SI units."""
        sp = {**_sample_state_point(), "unit_system": "SI"}
        inp = ReportInput(
            title="SI Report",
            unit_system="SI",
            pressure=101325.0,
            chart_image_base64=_minimal_png_b64(),
            state_points=[sp],
            include_sections=["chart", "state_points"],
        )
        pdf_bytes = generate_report(inp)
        assert pdf_bytes[:5] == b"%PDF-"

    def test_chart_only(self):
        """Generate a report with only the chart section."""
        inp = ReportInput(
            title="Chart Only",
            chart_image_base64=_minimal_png_b64(),
            include_sections=["chart"],
        )
        pdf_bytes = generate_report(inp)
        assert pdf_bytes[:5] == b"%PDF-"

    def test_notes_only(self):
        """Generate a report with only notes."""
        inp = ReportInput(
            title="Notes Only",
            chart_image_base64=_minimal_png_b64(),
            notes="Important project notes.",
            include_sections=["notes"],
        )
        pdf_bytes = generate_report(inp)
        assert pdf_bytes[:5] == b"%PDF-"

    def test_base64_with_data_uri_prefix(self):
        """Handle base64 data with data:image/png;base64, prefix."""
        b64 = _minimal_png_b64()
        inp = ReportInput(
            title="Data URI Test",
            chart_image_base64=f"data:image/png;base64,{b64}",
            include_sections=["chart"],
        )
        pdf_bytes = generate_report(inp)
        assert pdf_bytes[:5] == b"%PDF-"

    def test_empty_state_points_section_skipped(self):
        """Empty state points should not cause an error."""
        inp = ReportInput(
            title="Empty Points",
            chart_image_base64=_minimal_png_b64(),
            state_points=[],
            include_sections=["chart", "state_points"],
        )
        pdf_bytes = generate_report(inp)
        assert pdf_bytes[:5] == b"%PDF-"


# ── API tests ──


class TestReportAPI:
    """Test the /api/v1/report/generate endpoint."""

    def test_post_report(self):
        payload = {
            "title": "API Test Report",
            "chart_image_base64": _minimal_png_b64(),
            "state_points": [_sample_state_point()],
            "include_sections": ["chart", "state_points"],
        }
        resp = client.post("/api/v1/report/generate", json=payload)
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/pdf"
        assert resp.content[:5] == b"%PDF-"

    def test_post_full_report(self):
        payload = {
            "title": "Full API Report",
            "chart_image_base64": _minimal_png_b64(),
            "state_points": [_sample_state_point()],
            "processes": [_sample_process()],
            "coil_result": _sample_coil(),
            "notes": "Test notes",
            "include_sections": ["chart", "state_points", "processes", "coil", "notes"],
        }
        resp = client.post("/api/v1/report/generate", json=payload)
        assert resp.status_code == 200
        assert resp.content[:5] == b"%PDF-"

    def test_post_missing_chart_image(self):
        """chart_image_base64 is required."""
        payload = {
            "title": "No Chart",
            "include_sections": ["notes"],
            "notes": "Test",
        }
        resp = client.post("/api/v1/report/generate", json=payload)
        assert resp.status_code == 422
