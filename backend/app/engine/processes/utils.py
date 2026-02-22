"""
Shared utility functions for psychrometric process solvers.

These functions are used by multiple solvers (cooling_dehum, coil analysis, SHR)
and are extracted here to avoid duplication.
"""

import psychrolib
from scipy.optimize import brentq

from app.config import UnitSystem, GRAINS_PER_LB, CHART_RANGES
from app.models.process import PathPoint


def set_unit_system(unit_system: UnitSystem) -> None:
    """Configure psychrolib for the given unit system."""
    if unit_system == UnitSystem.IP:
        psychrolib.SetUnitSystem(psychrolib.IP)
    else:
        psychrolib.SetUnitSystem(psychrolib.SI)


def w_display(W: float, unit_system: UnitSystem) -> float:
    """Convert humidity ratio to display units (grains/lb IP or g/kg SI)."""
    if unit_system == UnitSystem.IP:
        return round(W * GRAINS_PER_LB, 4)
    else:
        return round(W * 1000.0, 4)


def find_adp(
    entering_Tdb: float,
    entering_W: float,
    leaving_Tdb: float,
    leaving_W: float,
    pressure: float,
    unit_system: UnitSystem,
) -> float:
    """
    Find the apparatus dew point (ADP) — the intersection of the process line
    with the saturation curve.

    The process line in Tdb-W space is:
        W = entering_W + slope × (Tdb - entering_Tdb)

    The ADP is where W_sat(Tdb) == W_line(Tdb).

    Returns the ADP dry-bulb temperature.
    """
    set_unit_system(unit_system)

    if abs(leaving_Tdb - entering_Tdb) < 1e-10:
        raise ValueError(
            "Entering and leaving Tdb are identical — cannot determine process line."
        )

    slope = (leaving_W - entering_W) / (leaving_Tdb - entering_Tdb)

    def objective(Tdb: float) -> float:
        W_on_line = entering_W + slope * (Tdb - entering_Tdb)
        W_sat = psychrolib.GetSatHumRatio(Tdb, pressure)
        return W_sat - W_on_line

    # Search domain: from chart minimum up to the leaving Tdb
    ranges = CHART_RANGES[unit_system.value]
    Tdb_min = ranges["Tdb_min"]
    Tdb_max = leaving_Tdb

    # Verify that the objective changes sign in the search interval
    f_min = objective(Tdb_min)
    f_max = objective(Tdb_max)

    if f_min * f_max > 0:
        raise ValueError(
            "Process line does not intersect the saturation curve. "
            "Check entering and leaving conditions."
        )

    adp_Tdb = brentq(objective, Tdb_min, Tdb_max, xtol=1e-8)
    return adp_Tdb


def generate_path_points(
    start_Tdb: float,
    start_W: float,
    end_Tdb: float,
    end_W: float,
    unit_system: UnitSystem,
    n_points: int = 12,
) -> list[PathPoint]:
    """Generate intermediate points along a straight process line."""
    points = []
    for i in range(n_points + 1):
        t = i / n_points
        Tdb = start_Tdb + t * (end_Tdb - start_Tdb)
        W = start_W + t * (end_W - start_W)
        points.append(PathPoint(
            Tdb=round(Tdb, 4),
            W=round(W, 7),
            W_display=w_display(W, unit_system),
        ))
    return points
