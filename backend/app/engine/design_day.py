"""
ASHRAE Design Day conditions engine.

Loads a curated JSON dataset of design day conditions by location,
supports searching, and resolves conditions to full psychrometric state points.
"""

import json
import os
from functools import lru_cache
from typing import Optional

import psychrolib

from app.config import UnitSystem, DEFAULT_PRESSURE_IP, DEFAULT_PRESSURE_SI

# Path to the bundled design day data
_DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "design_days.json")

# Human-readable labels for condition keys
_CONDITION_LABELS = {
    "cooling_db_004": "0.4% Cooling DB / MCWB",
    "cooling_db_010": "1.0% Cooling DB / MCWB",
    "cooling_db_020": "2.0% Cooling DB / MCWB",
    "cooling_wb_004": "0.4% Cooling WB / MCDB",
    "cooling_wb_010": "1.0% Cooling WB / MCDB",
    "cooling_wb_020": "2.0% Cooling WB / MCDB",
    "heating_996": "99.6% Heating DB",
    "heating_990": "99.0% Heating DB",
}

# Category mapping
_CONDITION_CATEGORIES = {
    "cooling_db_004": "cooling_db",
    "cooling_db_010": "cooling_db",
    "cooling_db_020": "cooling_db",
    "cooling_wb_004": "cooling_wb",
    "cooling_wb_010": "cooling_wb",
    "cooling_wb_020": "cooling_wb",
    "heating_996": "heating",
    "heating_990": "heating",
}


@lru_cache(maxsize=1)
def load_locations() -> list[dict]:
    """Load and cache the design day locations dataset."""
    with open(_DATA_PATH, "r") as f:
        return json.load(f)


def search_locations(query: str, limit: int = 20) -> list[dict]:
    """
    Search locations by city name or state, case-insensitive partial match.
    Returns abbreviated results sorted by relevance (exact prefix first).
    """
    locations = load_locations()
    query_lower = query.lower().strip()
    if not query_lower:
        return locations[:limit]

    results = []
    for loc in locations:
        name_lower = loc["name"].lower()
        state_lower = loc["state"].lower()
        full = f"{name_lower}, {state_lower}"

        # Score: exact prefix match on name is best
        if name_lower.startswith(query_lower):
            results.append((0, loc))
        elif query_lower in name_lower:
            results.append((1, loc))
        elif state_lower == query_lower:
            results.append((2, loc))
        elif query_lower in full:
            results.append((3, loc))

    results.sort(key=lambda x: x[0])
    return [r[1] for r in results[:limit]]


def _get_pressure_from_elevation(elevation_ft: float, unit_system: UnitSystem) -> float:
    """Compute barometric pressure from elevation."""
    if unit_system == "IP":
        psychrolib.SetUnitSystem(psychrolib.IP)
        return psychrolib.GetStandardAtmPressure(elevation_ft)
    else:
        psychrolib.SetUnitSystem(psychrolib.SI)
        elevation_m = elevation_ft * 0.3048
        return psychrolib.GetStandardAtmPressure(elevation_m)


def _parse_conditions(raw_conditions: dict) -> list[dict]:
    """Parse raw condition dict from JSON into structured condition list."""
    result = []
    for key, data in raw_conditions.items():
        label = _CONDITION_LABELS.get(key, key)
        category = _CONDITION_CATEGORIES.get(key, "unknown")

        if category in ("cooling_db",):
            result.append({
                "label": label,
                "category": category,
                "Tdb": data["Tdb"],
                "Twb_coincident": data.get("Twb_coincident"),
            })
        elif category in ("cooling_wb",):
            result.append({
                "label": label,
                "category": category,
                "Tdb_coincident": data.get("Tdb_coincident"),
                "Twb": data["Twb"],
            })
        elif category == "heating":
            result.append({
                "label": label,
                "category": category,
                "Tdb": data["Tdb"],
            })
    return result


def resolve_design_conditions(
    location_name: str,
    location_state: str,
    condition_labels: list[str],
    unit_system: UnitSystem,
    pressure_override: Optional[float] = None,
) -> dict:
    """
    Resolve design day conditions to full psychrometric state points.

    Args:
        location_name: City name to look up
        location_state: State abbreviation (helps disambiguate)
        condition_labels: Which conditions to resolve (empty = all)
        unit_system: "IP" or "SI"
        pressure_override: Override pressure; None = compute from elevation

    Returns:
        dict with location info, resolved points, and pressure used.
    """
    locations = load_locations()

    # Find the location
    location = None
    name_lower = location_name.lower().strip()
    state_lower = location_state.lower().strip()

    for loc in locations:
        if loc["name"].lower() == name_lower:
            if state_lower and loc["state"].lower() != state_lower:
                continue
            location = loc
            break

    if location is None:
        raise ValueError(f"Location '{location_name}' not found in design day database.")

    # Determine pressure
    if pressure_override is not None:
        pressure = pressure_override
    else:
        pressure = _get_pressure_from_elevation(location["elevation_ft"], unit_system)

    # Parse conditions
    parsed = _parse_conditions(location["conditions"])

    # Filter conditions if specific labels requested
    if condition_labels:
        label_set = set(condition_labels)
        parsed = [c for c in parsed if c["label"] in label_set]

    # Set psychrolib unit system
    if unit_system == "IP":
        psychrolib.SetUnitSystem(psychrolib.IP)
        w_factor = 7000.0  # grains/lb
    else:
        psychrolib.SetUnitSystem(psychrolib.SI)
        w_factor = 1000.0  # g/kg

    # Resolve each condition to a full state point
    resolved_points = []
    for cond in parsed:
        try:
            point = _resolve_single_condition(cond, pressure, unit_system, w_factor)
            if point is not None:
                resolved_points.append(point)
        except Exception:
            # Skip conditions that can't be resolved (e.g., heating with no Twb)
            continue

    return {
        "location": {
            "name": location["name"],
            "state": location["state"],
            "country": location["country"],
            "climate_zone": location["climate_zone"],
            "elevation_ft": location["elevation_ft"],
        },
        "points": resolved_points,
        "pressure_used": pressure,
        "unit_system": unit_system,
    }


def _resolve_single_condition(
    cond: dict, pressure: float, unit_system: str, w_factor: float
) -> Optional[dict]:
    """Resolve a single design condition to a full state point."""
    category = cond["category"]

    if category == "cooling_db":
        Tdb = cond["Tdb"]
        Twb = cond.get("Twb_coincident")
        if Twb is None:
            return None
        result = psychrolib.CalcPsychrometricsFromTWetBulb(Tdb, Twb, pressure)
        # Returns: (HumRatio, TDewPoint, RelHum, VapPres, MoistAirEnthalpy, MoistAirVolume, DegSaturation)
        W, Tdp, RH, _Pv, h, v, _mu = result

    elif category == "cooling_wb":
        Twb = cond["Twb"]
        Tdb = cond.get("Tdb_coincident")
        if Tdb is None:
            return None
        result = psychrolib.CalcPsychrometricsFromTWetBulb(Tdb, Twb, pressure)
        W, Tdp, RH, _Pv, h, v, _mu = result

    elif category == "heating":
        Tdb = cond["Tdb"]
        # For heating, we don't have Twb. Use a typical low winter RH.
        # Heating design points are typically just the dry-bulb.
        # Resolve at a nominal RH of 50% for plotting purposes.
        result = psychrolib.CalcPsychrometricsFromRelHum(Tdb, 0.50, pressure)
        W, Tdp, RH_resolved, _Pv, h, v, _mu = result
        Twb = psychrolib.GetTWetBulbFromHumRatio(Tdb, W, pressure)
        RH = 0.50

    else:
        return None

    return {
        "condition_label": cond["label"],
        "category": category,
        "Tdb": round(Tdb, 2),
        "Twb": round(Twb if isinstance(Twb, (int, float)) else 0.0, 2),
        "Tdp": round(Tdp, 2),
        "RH": round(RH * 100.0, 2),
        "W": W,
        "W_display": round(W * w_factor, 2),
        "h": round(h, 2),
        "v": round(v, 4),
        "unit_system": unit_system,
    }
