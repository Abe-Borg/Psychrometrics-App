"""
SHR (Sensible Heat Ratio) line engine.

Provides:
  - SHR line calculation: given room state + SHR → slope, line points, ADP
  - Grand SHR (GSHR): room loads + OA conditions → grand SHR
  - Effective SHR (ESHR): GSHR adjusted for coil bypass factor
"""

import psychrolib
from scipy.optimize import brentq

from app.config import UnitSystem, CHART_RANGES
from app.engine.state_resolver import resolve_state_point
from app.engine.processes.utils import set_unit_system, w_display
from app.models.process import PathPoint
from app.models.shr import (
    SHRLineInput,
    SHRLineOutput,
    GSHRInput,
    GSHROutput,
)


# Psychrometric constants
_CP_IP = 0.244    # BTU/(lb·°F)
_CP_SI = 1.006    # kJ/(kg·K)
_HFG_IP = 1061.0  # BTU/lb — latent heat of vaporization at ~60°F
_HFG_SI = 2501.0  # kJ/kg — latent heat of vaporization at ~0°C


def compute_shr_slope(shr: float, unit_system: UnitSystem) -> float:
    """
    Compute the slope dW/dTdb for a given SHR value.

    From the SHR definition:
        SHR = Qs / Qt = cp × ΔTdb / (cp × ΔTdb + hfg × ΔW)

    Rearranging:
        ΔW/ΔTdb = cp × (1 - SHR) / (hfg × SHR)

    Returns slope in W units (lb/lb per °F, or kg/kg per °C).
    For SHR=1.0 (pure sensible), slope is 0 (horizontal line).
    """
    if shr <= 0:
        raise ValueError("SHR must be greater than 0")
    if shr > 1.0:
        raise ValueError("SHR must not exceed 1.0")

    if shr == 1.0:
        return 0.0

    if unit_system == UnitSystem.IP:
        cp, hfg = _CP_IP, _HFG_IP
    else:
        cp, hfg = _CP_SI, _HFG_SI

    return cp * (1.0 - shr) / (hfg * shr)


def generate_shr_line(
    room_Tdb: float,
    room_W: float,
    slope: float,
    pressure: float,
    unit_system: UnitSystem,
    n_points: int = 50,
) -> list[PathPoint]:
    """
    Generate SHR line points extending from the saturation curve through the
    room point toward higher Tdb values.

    The line is clipped at the saturation curve on the low-Tdb side and
    at the chart Tdb_max on the high side.
    """
    set_unit_system(unit_system)
    ranges = CHART_RANGES[unit_system.value]

    # Find the Tdb bounds for the line
    Tdb_max = ranges["Tdb_max"]

    # On the low end, find where the SHR line meets the saturation curve
    # or the chart minimum, whichever comes first
    Tdb_min = ranges["Tdb_min"]

    # Generate points from Tdb_min to Tdb_max, keeping only valid ones
    points = []
    step = (Tdb_max - Tdb_min) / n_points

    for i in range(n_points + 1):
        Tdb = Tdb_min + i * step
        W = room_W + slope * (Tdb - room_Tdb)

        # Skip if W is negative
        if W < 0:
            continue

        # Skip if above saturation curve
        try:
            W_sat = psychrolib.GetSatHumRatio(Tdb, pressure)
            if W > W_sat * 1.01:  # small tolerance
                continue
        except Exception:
            continue

        points.append(PathPoint(
            Tdb=round(Tdb, 4),
            W=round(W, 7),
            W_display=w_display(W, unit_system),
        ))

    return points


def find_adp_from_shr(
    room_Tdb: float,
    room_W: float,
    slope: float,
    pressure: float,
    unit_system: UnitSystem,
) -> float:
    """
    Find the ADP (apparatus dew point) — the intersection of the SHR line
    with the saturation curve.

    SHR line: W = room_W + slope × (Tdb - room_Tdb)
    Saturation: W_sat(Tdb)

    Solve: W_sat(Tdb) = W_line(Tdb) for Tdb < room_Tdb.
    """
    set_unit_system(unit_system)
    ranges = CHART_RANGES[unit_system.value]

    def objective(Tdb: float) -> float:
        W_on_line = room_W + slope * (Tdb - room_Tdb)
        W_sat = psychrolib.GetSatHumRatio(Tdb, pressure)
        return W_sat - W_on_line

    # Search from chart minimum up to the room Tdb
    Tdb_min = ranges["Tdb_min"]
    Tdb_max = room_Tdb

    # Handle SHR=1.0 (slope=0, horizontal line) — intersection is at Tdp
    if abs(slope) < 1e-15:
        # Horizontal line at W=room_W, intersects saturation where W_sat(Tdb)=room_W
        # This is the dew point temperature
        def obj_horizontal(Tdb: float) -> float:
            return psychrolib.GetSatHumRatio(Tdb, pressure) - room_W
        try:
            adp_Tdb = brentq(obj_horizontal, Tdb_min, Tdb_max, xtol=1e-8)
            return adp_Tdb
        except ValueError:
            raise ValueError(
                "SHR line (horizontal) does not intersect the saturation curve."
            )

    f_min = objective(Tdb_min)
    f_max = objective(Tdb_max)

    if f_min * f_max > 0:
        raise ValueError(
            "SHR line does not intersect the saturation curve. "
            "Check room conditions and SHR value."
        )

    adp_Tdb = brentq(objective, Tdb_min, Tdb_max, xtol=1e-8)
    return adp_Tdb


def calculate_shr_line(shr_input: SHRLineInput) -> SHRLineOutput:
    """Calculate SHR line through room point with ADP intersection."""
    si = shr_input

    if si.shr <= 0 or si.shr > 1.0:
        raise ValueError("SHR must be between 0 (exclusive) and 1.0 (inclusive)")

    # Resolve room state
    room = resolve_state_point(
        input_pair=si.room_pair,
        values=si.room_values,
        pressure=si.pressure,
        unit_system=si.unit_system,
        label="room",
    )

    warnings: list[str] = []

    # Compute slope
    slope = compute_shr_slope(si.shr, si.unit_system)

    # Generate line points
    line_points = generate_shr_line(
        room.Tdb, room.W, slope, si.pressure, si.unit_system
    )

    # Find ADP
    adp_Tdb = find_adp_from_shr(
        room.Tdb, room.W, slope, si.pressure, si.unit_system
    )

    # Resolve ADP state
    adp = resolve_state_point(
        input_pair=("Tdb", "RH"),
        values=(adp_Tdb, 100.0),
        pressure=si.pressure,
        unit_system=si.unit_system,
        label="ADP",
    )

    return SHRLineOutput(
        room_point=room.model_dump(),
        shr=si.shr,
        slope_dW_dTdb=round(slope, 8),
        line_points=line_points,
        adp=adp.model_dump(),
        adp_Tdb=round(adp_Tdb, 4),
        warnings=warnings,
    )


def calculate_gshr(gshr_input: GSHRInput) -> GSHROutput:
    """
    Calculate Grand SHR (GSHR) and optionally Effective SHR (ESHR).

    GSHR accounts for both room loads and ventilation (outdoor air) loads.

    GSHR = Total Sensible / Total Heat = (Qs_room + Qs_oa) / (Qt_room + Qt_oa)

    Where OA loads are computed from the enthalpy/temperature difference
    between outdoor air and room air, scaled by the OA airflow fraction.
    """
    gi = gshr_input
    warnings: list[str] = []

    if gi.room_sensible_load > gi.room_total_load:
        raise ValueError(
            "Room sensible load cannot exceed room total load"
        )
    if gi.oa_fraction < 0 or gi.oa_fraction > 1:
        raise ValueError("OA fraction must be between 0 and 1")

    # Resolve room and OA states
    room = resolve_state_point(
        input_pair=gi.room_pair,
        values=gi.room_values,
        pressure=gi.pressure,
        unit_system=gi.unit_system,
        label="room",
    )
    oa = resolve_state_point(
        input_pair=gi.oa_pair,
        values=gi.oa_values,
        pressure=gi.pressure,
        unit_system=gi.unit_system,
        label="outdoor",
    )

    # Room SHR
    room_shr = gi.room_sensible_load / gi.room_total_load if gi.room_total_load > 0 else 1.0

    # Mixed air state (OA + return air)
    set_unit_system(gi.unit_system)
    oa_frac = gi.oa_fraction
    mixed_Tdb = room.Tdb + oa_frac * (oa.Tdb - room.Tdb)
    mixed_W = room.W + oa_frac * (oa.W - room.W)

    mixed = resolve_state_point(
        input_pair=("Tdb", "W"),
        values=(mixed_Tdb, mixed_W),
        pressure=gi.pressure,
        unit_system=gi.unit_system,
        label="mixed",
    )

    # OA ventilation loads
    # Qs_oa based on temperature difference between OA and room
    # Qt_oa based on enthalpy difference between OA and room
    if gi.unit_system == UnitSystem.IP:
        cp = _CP_IP
        # C factor for airflow conversion
        rho = 1.0 / room.v
        C_sensible = 60.0 * rho * cp
        oa_cfm = gi.total_airflow * oa_frac
        Qs_oa = C_sensible * oa_cfm * (oa.Tdb - room.Tdb)
        Qt_oa = 4.5 * oa_cfm * (oa.h - room.h)
    else:
        cp = _CP_SI
        rho = 1.0 / room.v
        oa_flow = gi.total_airflow * oa_frac
        mass_flow_oa = rho * oa_flow
        Qs_oa = mass_flow_oa * cp * (oa.Tdb - room.Tdb) * 1000  # W
        Qt_oa = mass_flow_oa * (oa.h - room.h) * 1000  # W

    # Grand SHR
    total_sensible = gi.room_sensible_load + Qs_oa
    total_heat = gi.room_total_load + Qt_oa

    if total_heat <= 0:
        warnings.append("Total heat load is non-positive. GSHR cannot be computed.")
        gshr = 1.0
    else:
        gshr = total_sensible / total_heat

    if gshr < 0 or gshr > 1:
        warnings.append(
            f"Computed GSHR ({gshr:.3f}) is outside the normal range (0-1). "
            "Check load values and OA conditions."
        )

    # SHR lines through room point
    room_slope = compute_shr_slope(max(0.01, min(room_shr, 1.0)), gi.unit_system)
    room_shr_line = generate_shr_line(
        room.Tdb, room.W, room_slope, gi.pressure, gi.unit_system
    )
    room_shr_adp_Tdb = find_adp_from_shr(
        room.Tdb, room.W, room_slope, gi.pressure, gi.unit_system
    )
    room_shr_adp = resolve_state_point(
        input_pair=("Tdb", "RH"),
        values=(room_shr_adp_Tdb, 100.0),
        pressure=gi.pressure,
        unit_system=gi.unit_system,
        label="RSHRADP",
    )

    # GSHR line through room point
    gshr_clamped = max(0.01, min(gshr, 1.0))
    gshr_slope = compute_shr_slope(gshr_clamped, gi.unit_system)
    gshr_line = generate_shr_line(
        room.Tdb, room.W, gshr_slope, gi.pressure, gi.unit_system
    )
    gshr_adp_Tdb = find_adp_from_shr(
        room.Tdb, room.W, gshr_slope, gi.pressure, gi.unit_system
    )
    gshr_adp = resolve_state_point(
        input_pair=("Tdb", "RH"),
        values=(gshr_adp_Tdb, 100.0),
        pressure=gi.pressure,
        unit_system=gi.unit_system,
        label="GSHRADP",
    )

    # ESHR (Effective SHR) if BF provided
    eshr = None
    eshr_line = None
    eshr_adp = None
    if gi.bypass_factor is not None:
        bf = gi.bypass_factor
        if not (0.0 < bf < 1.0):
            raise ValueError("bypass_factor must be between 0 and 1 (exclusive)")

        # ESHR = (GSHR × (1 - BF × CF_fraction)) simplified to:
        # The effective coil load line accounts for bypassed air re-entering.
        # ESHR ≈ 1 - (1 - GSHR) / (1 - BF)
        # More precisely: ESHR_load = room_load + BF/(1-BF) × room_load_through_coil
        # Standard textbook: ESHR = (total_sensible + BF × Qt_bypass) / (total_heat + Qt_bypass)
        # Simplified standard form:
        eshr = 1.0 - (1.0 - gshr) / (1.0 - bf)

        if eshr < 0 or eshr > 1:
            warnings.append(
                f"Computed ESHR ({eshr:.3f}) is outside the normal range (0-1). "
                "The combination of GSHR and BF may be invalid."
            )
            eshr = max(0.01, min(eshr, 1.0))

        eshr_slope = compute_shr_slope(max(0.01, min(eshr, 1.0)), gi.unit_system)
        eshr_line = generate_shr_line(
            room.Tdb, room.W, eshr_slope, gi.pressure, gi.unit_system
        )
        eshr_adp_Tdb = find_adp_from_shr(
            room.Tdb, room.W, eshr_slope, gi.pressure, gi.unit_system
        )
        eshr_adp = resolve_state_point(
            input_pair=("Tdb", "RH"),
            values=(eshr_adp_Tdb, 100.0),
            pressure=gi.pressure,
            unit_system=gi.unit_system,
            label="ESHRADP",
        )
        eshr_adp = eshr_adp.model_dump()
        eshr = round(eshr, 4)

    return GSHROutput(
        room_point=room.model_dump(),
        oa_point=oa.model_dump(),
        mixed_point=mixed.model_dump(),
        room_shr=round(room_shr, 4),
        gshr=round(gshr, 4),
        eshr=eshr,
        room_shr_line=room_shr_line,
        gshr_line=gshr_line,
        eshr_line=eshr_line,
        room_shr_adp=room_shr_adp.model_dump(),
        gshr_adp=gshr_adp.model_dump(),
        eshr_adp=eshr_adp,
        warnings=warnings,
    )
