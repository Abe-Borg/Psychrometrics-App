"""
TMY3 data parser and bin processor.

Parses Typical Meteorological Year CSV files (TMY3 format from NREL),
extracts hourly Tdb and humidity data, computes psychrometric properties,
and bins data into a 2D grid for heatmap visualization.
"""

import csv
import io
from typing import Optional

import numpy as np
import psychrolib

from app.config import UnitSystem


def parse_tmy3(
    file_content: str,
    unit_system: UnitSystem,
    pressure: float,
    tdb_bin_size: float = 5.0,
    w_bin_size: Optional[float] = None,
) -> dict:
    """
    Parse a TMY3 CSV file and return scatter points + binned heatmap data.

    TMY3 format (NREL):
    - Row 1: station metadata (station number, city, state, etc.)
    - Row 2: column headers
    - Rows 3+: 8760 hourly data rows

    Key columns (vary by format version):
    - Dry-bulb temperature (C)
    - Dew-point temperature (C) or RH (%)

    Args:
        file_content: Raw CSV text
        unit_system: "IP" or "SI"
        pressure: Atmospheric pressure
        tdb_bin_size: Bin size for Tdb axis (default 5°F or 5°C)
        w_bin_size: Bin size for W axis (default auto-computed)

    Returns:
        dict matching TMYProcessOutput schema
    """
    lines = file_content.strip().splitlines()
    if len(lines) < 10:
        raise ValueError("File too short to be a valid TMY3 file.")

    # Try to detect TMY3 format:
    # Classic TMY3: first line is metadata, second is headers
    # Try to find temperature column indices
    location_name = _extract_location_name(lines[0])

    # Parse headers from row 2 (index 1)
    reader = csv.reader(io.StringIO(lines[1]))
    headers = next(reader)
    headers_lower = [h.strip().lower() for h in headers]

    # Find column indices
    tdb_col = _find_column(headers_lower, [
        "dry-bulb (c)", "dry bulb temperature",
        "dry-bulb temperature", "tdb", "drybulb",
        "dry bulb (c)", "dry-bulb",
    ])
    # Try dew point first, then RH
    tdp_col = _find_column(headers_lower, [
        "dew-point (c)", "dew point temperature",
        "dew-point temperature", "tdp", "dewpoint",
        "dew point (c)", "dew-point",
    ])
    rh_col = _find_column(headers_lower, [
        "rhum(%)", "rh(%)", "relative humidity",
        "rh", "rhum", "humidity",
    ])

    if tdb_col is None:
        raise ValueError(
            f"Could not find dry-bulb temperature column. Headers: {headers[:10]}"
        )
    if tdp_col is None and rh_col is None:
        raise ValueError(
            "Could not find dew-point or RH column in TMY3 file."
        )

    # Parse data rows (starting from row 3, index 2)
    scatter_points = []
    hour = 0

    # Set up psychrolib for W calculation
    # TMY3 data is always in SI (°C), we convert to target unit system
    psychrolib.SetUnitSystem(psychrolib.SI)

    # Determine SI pressure for psychrolib calcs
    if unit_system == "IP":
        pressure_si = pressure * 6894.76  # psia to Pa
        w_factor = 7000.0  # grains/lb
    else:
        pressure_si = pressure
        w_factor = 1000.0  # g/kg

    for line_idx in range(2, len(lines)):
        line = lines[line_idx].strip()
        if not line:
            continue

        try:
            reader = csv.reader(io.StringIO(line))
            row = next(reader)

            tdb_c = float(row[tdb_col])

            if tdp_col is not None:
                tdp_c = float(row[tdp_col])
                W = psychrolib.GetHumRatioFromTDewPoint(tdp_c, pressure_si)
            else:
                rh = float(row[rh_col]) / 100.0
                W = psychrolib.GetHumRatioFromRelHum(tdb_c, rh, pressure_si)

            # Convert to target unit system
            if unit_system == "IP":
                tdb_display = tdb_c * 9.0 / 5.0 + 32.0
            else:
                tdb_display = tdb_c

            W_display = W * w_factor

            # Determine month from row date (first column typically has date/time)
            month = _extract_month(row, line_idx - 2)

            scatter_points.append({
                "Tdb": round(tdb_display, 2),
                "W_display": round(W_display, 2),
                "hour": hour,
                "month": month,
            })
            hour += 1
        except (ValueError, IndexError):
            continue

    if len(scatter_points) == 0:
        raise ValueError("No valid data points found in TMY3 file.")

    # Bin the data
    if w_bin_size is None:
        w_bin_size = 10.0 if unit_system == "IP" else 2.0

    bin_result = _bin_data(scatter_points, tdb_bin_size, w_bin_size)

    return {
        "unit_system": unit_system,
        "scatter_points": scatter_points,
        "bin_Tdb_edges": bin_result["tdb_edges"],
        "bin_W_edges": bin_result["w_edges"],
        "bin_matrix": bin_result["matrix"],
        "location_name": location_name,
        "total_hours": len(scatter_points),
    }


def _extract_location_name(first_line: str) -> Optional[str]:
    """Try to extract location name from TMY3 metadata line."""
    try:
        parts = first_line.split(",")
        if len(parts) >= 3:
            # TMY3 format: station_id, city, state, ...
            city = parts[1].strip().strip('"')
            state = parts[2].strip().strip('"')
            if city and state:
                return f"{city}, {state}"
            return city or None
    except Exception:
        pass
    return None


def _find_column(headers: list[str], candidates: list[str]) -> Optional[int]:
    """Find column index matching one of the candidate names."""
    for candidate in candidates:
        for i, h in enumerate(headers):
            if candidate in h:
                return i
    return None


def _extract_month(row: list[str], hour_index: int) -> int:
    """Extract month from TMY3 row or compute from hour index."""
    # Try to parse date from first column (format varies: MM/DD/YYYY or YYYY-MM-DD)
    try:
        date_str = row[0].strip()
        if "/" in date_str:
            parts = date_str.split("/")
            return int(parts[0])
        elif "-" in date_str:
            parts = date_str.split("-")
            return int(parts[1])
    except (ValueError, IndexError):
        pass

    # Fallback: compute from hour index (0-8759)
    days_per_month = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    hours_per_month = [d * 24 for d in days_per_month]
    cumulative = 0
    for m, h in enumerate(hours_per_month):
        cumulative += h
        if hour_index < cumulative:
            return m + 1
    return 12


def _bin_data(
    scatter_points: list[dict],
    tdb_bin_size: float,
    w_bin_size: float,
) -> dict:
    """Bin scatter points into a 2D grid for heatmap display."""
    tdbs = np.array([p["Tdb"] for p in scatter_points])
    ws = np.array([p["W_display"] for p in scatter_points])

    # Create bin edges
    tdb_min = np.floor(tdbs.min() / tdb_bin_size) * tdb_bin_size
    tdb_max = np.ceil(tdbs.max() / tdb_bin_size) * tdb_bin_size
    w_min = np.floor(ws.min() / w_bin_size) * w_bin_size
    w_max = np.ceil(ws.max() / w_bin_size) * w_bin_size

    tdb_edges = np.arange(tdb_min, tdb_max + tdb_bin_size, tdb_bin_size)
    w_edges = np.arange(w_min, w_max + w_bin_size, w_bin_size)

    # Create 2D histogram
    matrix, _, _ = np.histogram2d(ws, tdbs, bins=[w_edges, tdb_edges])

    return {
        "tdb_edges": [round(float(e), 2) for e in tdb_edges],
        "w_edges": [round(float(e), 2) for e in w_edges],
        "matrix": [[int(c) for c in row] for row in matrix.tolist()],
    }
