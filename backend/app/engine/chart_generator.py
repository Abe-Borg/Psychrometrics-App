"""
Chart background data generator.

Generates all the reference lines needed to render a psychrometric chart:
- Saturation curve (100% RH)
- Constant relative humidity lines (10%, 20%, ... 90%)
- Constant wet-bulb temperature lines
- Constant enthalpy lines
- Constant specific volume lines

Each generator sweeps across a range of dry-bulb temperatures and computes
the corresponding humidity ratio for a given constant property value.
All math is via psychrolib — no approximations.
"""

import psychrolib
import numpy as np
from app.config import UnitSystem, CHART_RANGES, GRAINS_PER_LB


def _set_unit_system(unit_system: UnitSystem) -> None:
    if unit_system == UnitSystem.IP:
        psychrolib.SetUnitSystem(psychrolib.IP)
    else:
        psychrolib.SetUnitSystem(psychrolib.SI)


def _w_to_display(W: float, unit_system: UnitSystem) -> float:
    """Convert humidity ratio to display units (grains for IP, g/kg for SI)."""
    if unit_system == UnitSystem.IP:
        return W * GRAINS_PER_LB
    else:
        return W * 1000.0


def _get_tdb_range(unit_system: UnitSystem, num_points: int = 200) -> np.ndarray:
    """Get the array of dry-bulb temperatures to sweep across."""
    ranges = CHART_RANGES[unit_system.value]
    return np.linspace(ranges["Tdb_min"], ranges["Tdb_max"], num_points)


def generate_saturation_curve(
    pressure: float, unit_system: UnitSystem, num_points: int = 200
) -> list[dict]:
    """
    Generate the saturation curve (100% RH boundary).

    Returns list of {Tdb, W, W_display} points tracing the upper boundary
    of the psychrometric chart.
    """
    _set_unit_system(unit_system)
    tdb_range = _get_tdb_range(unit_system, num_points)
    points = []

    for Tdb in tdb_range:
        try:
            W = psychrolib.GetSatHumRatio(float(Tdb), pressure)
            if W >= 0:
                points.append({
                    "Tdb": round(float(Tdb), 2),
                    "W": round(W, 7),
                    "W_display": round(_w_to_display(W, unit_system), 2),
                })
        except Exception:
            continue

    return points


def generate_rh_lines(
    pressure: float, unit_system: UnitSystem, num_points: int = 200
) -> dict[str, list[dict]]:
    """
    Generate constant relative humidity lines.

    Returns dict keyed by RH percentage string (e.g., "10", "20", ... "90"),
    each containing a list of {Tdb, W, W_display} points.
    """
    _set_unit_system(unit_system)
    tdb_range = _get_tdb_range(unit_system, num_points)
    rh_values = [10, 20, 30, 40, 50, 60, 70, 80, 90]
    w_max = CHART_RANGES[unit_system.value]["W_max"]

    lines = {}
    for rh_pct in rh_values:
        rh = rh_pct / 100.0
        points = []
        for Tdb in tdb_range:
            try:
                W = psychrolib.GetHumRatioFromRelHum(float(Tdb), rh, pressure)
                W_disp = _w_to_display(W, unit_system)
                if W >= 0 and W_disp <= w_max:
                    points.append({
                        "Tdb": round(float(Tdb), 2),
                        "W": round(W, 7),
                        "W_display": round(W_disp, 2),
                    })
            except Exception:
                continue
        lines[str(rh_pct)] = points

    return lines


def generate_twb_lines(
    pressure: float, unit_system: UnitSystem, num_points: int = 150
) -> dict[str, list[dict]]:
    """
    Generate constant wet-bulb temperature lines.

    For each target Twb, we sweep Tdb from Twb upward (since Tdb >= Twb)
    and find the W that produces that Twb at each Tdb.

    psychrolib's GetHumRatioFromTWetBulb(Tdb, Twb, P) does exactly this.
    """
    _set_unit_system(unit_system)
    ranges = CHART_RANGES[unit_system.value]
    w_max = ranges["W_max"]

    # Choose Twb values to draw
    if unit_system == UnitSystem.IP:
        twb_values = list(range(30, 90, 5))  # 30°F to 85°F in 5°F steps
    else:
        twb_values = list(range(0, 35, 2))  # 0°C to 34°C in 2°C steps

    lines = {}
    for twb in twb_values:
        points = []
        # Tdb ranges from Twb to the chart max
        tdb_start = float(twb)
        tdb_end = ranges["Tdb_max"]
        tdb_sweep = np.linspace(tdb_start, tdb_end, num_points)

        for Tdb in tdb_sweep:
            try:
                W = psychrolib.GetHumRatioFromTWetBulb(float(Tdb), float(twb), pressure)
                W_disp = _w_to_display(W, unit_system)
                if W >= 0 and W_disp <= w_max:
                    points.append({
                        "Tdb": round(float(Tdb), 2),
                        "W": round(W, 7),
                        "W_display": round(W_disp, 2),
                    })
            except Exception:
                continue

        if len(points) >= 2:
            lines[str(twb)] = points

    return lines


def generate_enthalpy_lines(
    pressure: float, unit_system: UnitSystem, num_points: int = 150
) -> dict[str, list[dict]]:
    """
    Generate constant enthalpy lines.

    For a given enthalpy h, the relationship is:
        h = Cp_da * Tdb + W * (h_fg + Cp_wv * Tdb)

    Solving for W:
        IP:  W = (h - 0.240 * Tdb) / (1061.0 + 0.444 * Tdb)
        SI:  W = (h - 1.006 * Tdb * 1000) / (2501000 + 1860 * Tdb)
             (psychrolib uses J/kg internally for SI)

    We sweep Tdb across the chart range and compute W at each point,
    keeping only points where W >= 0 and within chart bounds.
    """
    _set_unit_system(unit_system)
    ranges = CHART_RANGES[unit_system.value]
    w_max = ranges["W_max"]
    tdb_range = _get_tdb_range(unit_system, num_points)

    # Choose enthalpy values
    if unit_system == UnitSystem.IP:
        # BTU/lb_da — typical range 10 to 55 in steps of 5
        h_values = list(range(10, 56, 5))
    else:
        # kJ/kg_da — typical range 10 to 120 in steps of 10
        # psychrolib SI uses J/kg internally, but we'll work in kJ/kg for labels
        # and convert to J/kg for calculations
        h_values = list(range(10, 121, 10))

    lines = {}
    for h_val in h_values:
        points = []
        for Tdb in tdb_range:
            try:
                # Solve W from enthalpy equation
                if unit_system == UnitSystem.IP:
                    # h = 0.240 * Tdb + W * (1061 + 0.444 * Tdb)
                    denom = 1061.0 + 0.444 * float(Tdb)
                    W = (float(h_val) - 0.240 * float(Tdb)) / denom
                else:
                    # psychrolib SI enthalpy is in J/kg_da
                    # h = 1006 * Tdb + W * (2501000 + 1860 * Tdb)
                    h_si = float(h_val) * 1000.0  # kJ to J
                    denom = 2501000.0 + 1860.0 * float(Tdb)
                    W = (h_si - 1006.0 * float(Tdb)) / denom

                W_disp = _w_to_display(W, unit_system)
                if W >= 0 and W_disp <= w_max and W_disp >= 0:
                    points.append({
                        "Tdb": round(float(Tdb), 2),
                        "W": round(W, 7),
                        "W_display": round(W_disp, 2),
                    })
            except Exception:
                continue

        if len(points) >= 2:
            lines[str(h_val)] = points

    return lines


def generate_volume_lines(
    pressure: float, unit_system: UnitSystem, num_points: int = 150
) -> dict[str, list[dict]]:
    """
    Generate constant specific volume lines.

    For a given specific volume v, we sweep Tdb and find W such that
    GetMoistAirVolume(Tdb, W, pressure) == v_target.

    The moist air volume equation is approximately:
        IP:  v = 0.370486 * (Tdb + 459.67) * (1 + 1.607858 * W) / P
        SI:  v = 0.287042 * (Tdb + 273.15) * (1 + 1.607858 * W) / P

    Solving for W:
        W = (v * P / (R_da * T) - 1) / 1.607858

    where R_da = 0.370486 (IP) or 287.042 (SI), T = Tdb + 459.67 (IP) or Tdb + 273.15 (SI)
    """
    _set_unit_system(unit_system)
    ranges = CHART_RANGES[unit_system.value]
    w_max = ranges["W_max"]
    tdb_range = _get_tdb_range(unit_system, num_points)

    # Choose volume values
    if unit_system == UnitSystem.IP:
        # ft³/lb_da — typical range 12.5 to 15.0 in steps of 0.5
        v_values = [round(x * 0.1, 1) for x in range(125, 151, 5)]
    else:
        # m³/kg_da — typical range 0.78 to 0.98 in steps of 0.02
        v_values = [round(x * 0.01, 2) for x in range(78, 99, 2)]

    lines = {}
    for v_target in v_values:
        points = []
        for Tdb in tdb_range:
            try:
                if unit_system == UnitSystem.IP:
                    T_abs = float(Tdb) + 459.67
                    R_da = 0.370486
                else:
                    T_abs = float(Tdb) + 273.15
                    R_da = 287.042

                W = ((float(v_target) * float(pressure)) / (R_da * T_abs) - 1.0) / 1.607858

                W_disp = _w_to_display(W, unit_system)
                if W >= 0 and W_disp <= w_max and W_disp >= 0:
                    # Verify with psychrolib
                    v_check = psychrolib.GetMoistAirVolume(float(Tdb), W, pressure)
                    if abs(v_check - v_target) < 0.01 * v_target:
                        points.append({
                            "Tdb": round(float(Tdb), 2),
                            "W": round(W, 7),
                            "W_display": round(W_disp, 2),
                        })
            except Exception:
                continue

        if len(points) >= 2:
            lines[str(v_target)] = points

    return lines


def generate_chart_data(pressure: float, unit_system: UnitSystem) -> dict:
    """
    Generate all chart background data in a single call.

    Returns a dict containing all line sets needed to render the full
    psychrometric chart background.
    """
    return {
        "unit_system": unit_system.value,
        "pressure": pressure,
        "ranges": CHART_RANGES[unit_system.value],
        "saturation_curve": generate_saturation_curve(pressure, unit_system),
        "rh_lines": generate_rh_lines(pressure, unit_system),
        "twb_lines": generate_twb_lines(pressure, unit_system),
        "enthalpy_lines": generate_enthalpy_lines(pressure, unit_system),
        "volume_lines": generate_volume_lines(pressure, unit_system),
    }
