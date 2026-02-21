"""
Core state point resolver.

Given any supported pair of independent psychrometric properties and atmospheric
pressure, resolves all other psychrometric properties using psychrolib.

For input pairs that psychrolib doesn't support directly (e.g., Tdb+h, Twb+RH),
we use scipy root-finding to converge on the solution.
"""

import psychrolib
from scipy.optimize import brentq

from app.config import (
    UnitSystem,
    SUPPORTED_INPUT_PAIRS,
    GRAINS_PER_LB,
)
from app.models.state_point import StatePointOutput


def _set_unit_system(unit_system: UnitSystem) -> None:
    """Set psychrolib's global unit system."""
    if unit_system == UnitSystem.IP:
        psychrolib.SetUnitSystem(psychrolib.IP)
    else:
        psychrolib.SetUnitSystem(psychrolib.SI)


def _get_sat_press(Tdb: float) -> float:
    """Get saturation vapor pressure at a given dry-bulb temperature."""
    return psychrolib.GetSatVapPres(Tdb)


def _calc_all_from_tdb_w(
    Tdb: float, W: float, pressure: float, unit_system: UnitSystem
) -> dict:
    """
    Given Tdb and W (humidity ratio), calculate all other properties.
    This is our canonical resolution path — most input pairs ultimately
    get converted to Tdb + W, and then we compute everything else.
    """
    _set_unit_system(unit_system)

    # Core calculations from psychrolib
    Twb = psychrolib.GetTWetBulbFromHumRatio(Tdb, W, pressure)
    Tdp = psychrolib.GetTDewPointFromHumRatio(Tdb, W, pressure)
    RH = psychrolib.GetRelHumFromHumRatio(Tdb, W, pressure)
    h = psychrolib.GetMoistAirEnthalpy(Tdb, W)
    v = psychrolib.GetMoistAirVolume(Tdb, W, pressure)
    Ps = psychrolib.GetSatVapPres(Tdb)
    Pv = psychrolib.GetVapPresFromHumRatio(W, pressure)

    # Degree of saturation: ratio of actual W to saturation W at same Tdb
    W_sat = psychrolib.GetSatHumRatio(Tdb, pressure)
    mu = W / W_sat if W_sat > 0 else 0.0

    # Display humidity ratio (grains for IP, g/kg for SI)
    if unit_system == UnitSystem.IP:
        W_display = W * GRAINS_PER_LB
    else:
        W_display = W * 1000.0  # kg/kg → g/kg

    # RH as percentage (psychrolib returns 0-1)
    RH_pct = RH * 100.0

    return {
        "Tdb": round(Tdb, 4),
        "Twb": round(Twb, 4),
        "Tdp": round(Tdp, 4),
        "RH": round(RH_pct, 4),
        "W": round(W, 7),
        "W_display": round(W_display, 4),
        "h": round(h, 4),
        "v": round(v, 4),
        "Pv": round(Pv, 6),
        "Ps": round(Ps, 6),
        "mu": round(mu, 6),
    }


def _resolve_tdb_rh(Tdb: float, RH_pct: float, pressure: float, unit_system: UnitSystem) -> dict:
    """Resolve from dry-bulb temperature and relative humidity."""
    _set_unit_system(unit_system)
    RH = RH_pct / 100.0  # psychrolib expects 0-1
    W = psychrolib.GetHumRatioFromRelHum(Tdb, RH, pressure)
    return _calc_all_from_tdb_w(Tdb, W, pressure, unit_system)


def _resolve_tdb_twb(Tdb: float, Twb: float, pressure: float, unit_system: UnitSystem) -> dict:
    """Resolve from dry-bulb and wet-bulb temperatures."""
    _set_unit_system(unit_system)
    W = psychrolib.GetHumRatioFromTWetBulb(Tdb, Twb, pressure)
    return _calc_all_from_tdb_w(Tdb, W, pressure, unit_system)


def _resolve_tdb_tdp(Tdb: float, Tdp: float, pressure: float, unit_system: UnitSystem) -> dict:
    """Resolve from dry-bulb and dew point temperatures."""
    _set_unit_system(unit_system)
    W = psychrolib.GetHumRatioFromTDewPoint(Tdp, pressure)
    return _calc_all_from_tdb_w(Tdb, W, pressure, unit_system)


def _resolve_tdb_w(Tdb: float, W: float, pressure: float, unit_system: UnitSystem) -> dict:
    """Resolve from dry-bulb temperature and humidity ratio (lb/lb or kg/kg)."""
    return _calc_all_from_tdb_w(Tdb, W, pressure, unit_system)


def _resolve_tdb_h(Tdb: float, h_target: float, pressure: float, unit_system: UnitSystem) -> dict:
    """
    Resolve from dry-bulb temperature and specific enthalpy.

    psychrolib doesn't have a direct GetHumRatioFromEnthalpy function,
    so we use root-finding: find W such that GetMoistAirEnthalpy(Tdb, W) == h_target.

    The enthalpy equation is: h = 0.240 * Tdb + W * (1061 + 0.444 * Tdb) [IP]
    This is linear in W, so we can actually solve directly:
        W = (h - 0.240 * Tdb) / (1061 + 0.444 * Tdb)  [IP]
        W = (h - 1.006 * Tdb) / (2501 + 1.86 * Tdb)    [SI, kJ/kg with Tdb in °C]

    But we'll use the general solver approach for robustness.
    """
    _set_unit_system(unit_system)

    def objective(W: float) -> float:
        h_calc = psychrolib.GetMoistAirEnthalpy(Tdb, W)
        return h_calc - h_target

    # W bounds: 0 to saturation
    W_sat = psychrolib.GetSatHumRatio(Tdb, pressure)
    W_min = 0.0

    # Check if the target enthalpy is achievable at this Tdb
    h_at_min = psychrolib.GetMoistAirEnthalpy(Tdb, W_min)
    h_at_max = psychrolib.GetMoistAirEnthalpy(Tdb, W_sat)

    if h_target < h_at_min or h_target > h_at_max:
        raise ValueError(
            f"Target enthalpy {h_target} is outside the achievable range "
            f"[{h_at_min:.2f}, {h_at_max:.2f}] at Tdb={Tdb}"
        )

    W = brentq(objective, W_min, W_sat, xtol=1e-10)
    return _calc_all_from_tdb_w(Tdb, W, pressure, unit_system)


def _resolve_twb_rh(Twb: float, RH_pct: float, pressure: float, unit_system: UnitSystem) -> dict:
    """
    Resolve from wet-bulb temperature and relative humidity.

    psychrolib doesn't support this directly. We find Tdb such that:
    - GetHumRatioFromTWetBulb(Tdb, Twb, pressure) gives a W, and
    - GetRelHumFromHumRatio(Tdb, W, pressure) == target RH
    """
    _set_unit_system(unit_system)
    RH = RH_pct / 100.0

    def objective(Tdb: float) -> float:
        W = psychrolib.GetHumRatioFromTWetBulb(Tdb, Twb, pressure)
        if W < 0:
            return -1.0  # invalid region
        RH_calc = psychrolib.GetRelHumFromHumRatio(Tdb, W, pressure)
        return RH_calc - RH

    # Tdb must be >= Twb (dry-bulb is always >= wet-bulb)
    # Upper bound: pick a reasonable max
    Tdb_min = Twb
    if unit_system == UnitSystem.IP:
        Tdb_max = 200.0
    else:
        Tdb_max = 90.0

    # At Tdb == Twb, RH == 100%. As Tdb increases, RH decreases.
    # So if target RH < 100%, Tdb > Twb.
    try:
        Tdb = brentq(objective, Tdb_min, Tdb_max, xtol=1e-8)
    except ValueError:
        raise ValueError(
            f"Cannot find a valid Tdb for Twb={Twb}, RH={RH_pct}%"
        )

    W = psychrolib.GetHumRatioFromTWetBulb(Tdb, Twb, pressure)
    return _calc_all_from_tdb_w(Tdb, W, pressure, unit_system)


def _resolve_tdp_rh(Tdp: float, RH_pct: float, pressure: float, unit_system: UnitSystem) -> dict:
    """
    Resolve from dew point temperature and relative humidity.

    Given Tdp, the vapor pressure is fixed: Pv = GetSatVapPres(Tdp).
    Given RH, we have: RH = Pv / Ps(Tdb), so Ps(Tdb) = Pv / RH.
    We find Tdb such that GetSatVapPres(Tdb) == Pv / RH.
    """
    _set_unit_system(unit_system)
    RH = RH_pct / 100.0

    Pv = psychrolib.GetSatVapPres(Tdp)
    Ps_target = Pv / RH

    def objective(Tdb: float) -> float:
        Ps_calc = psychrolib.GetSatVapPres(Tdb)
        return Ps_calc - Ps_target

    # Tdb must be >= Tdp
    Tdb_min = Tdp
    if unit_system == UnitSystem.IP:
        Tdb_max = 200.0
    else:
        Tdb_max = 90.0

    try:
        Tdb = brentq(objective, Tdb_min, Tdb_max, xtol=1e-8)
    except ValueError:
        raise ValueError(
            f"Cannot find a valid Tdb for Tdp={Tdp}, RH={RH_pct}%"
        )

    W = psychrolib.GetHumRatioFromTDewPoint(Tdp, pressure)
    return _calc_all_from_tdb_w(Tdb, W, pressure, unit_system)


# Resolver dispatch table
_RESOLVERS = {
    ("Tdb", "RH"): _resolve_tdb_rh,
    ("Tdb", "Twb"): _resolve_tdb_twb,
    ("Tdb", "Tdp"): _resolve_tdb_tdp,
    ("Tdb", "W"): _resolve_tdb_w,
    ("Tdb", "h"): _resolve_tdb_h,
    ("Twb", "RH"): _resolve_twb_rh,
    ("Tdp", "RH"): _resolve_tdp_rh,
}


def resolve_state_point(
    input_pair: tuple[str, str],
    values: tuple[float, float],
    pressure: float,
    unit_system: UnitSystem,
    label: str = "",
) -> StatePointOutput:
    """
    Main entry point. Resolves a full state point from any supported input pair.

    Args:
        input_pair: Tuple of two property names, e.g. ("Tdb", "RH")
        values: Tuple of two values corresponding to the input pair
        pressure: Atmospheric pressure (psia for IP, Pa for SI)
        unit_system: IP or SI
        label: Optional user label

    Returns:
        StatePointOutput with all resolved properties

    Raises:
        ValueError: If the input pair is not supported or values are out of range
    """
    pair = tuple(input_pair)

    # Check if pair is supported (or its reverse)
    if pair not in _RESOLVERS:
        reverse_pair = (pair[1], pair[0])
        if reverse_pair in _RESOLVERS:
            pair = reverse_pair
            values = (values[1], values[0])
        else:
            supported = [f"({a}, {b})" for a, b in SUPPORTED_INPUT_PAIRS]
            raise ValueError(
                f"Unsupported input pair: {input_pair}. "
                f"Supported pairs: {', '.join(supported)}"
            )

    resolver = _RESOLVERS[pair]
    props = resolver(values[0], values[1], pressure, unit_system)

    return StatePointOutput(
        label=label,
        unit_system=unit_system,
        pressure=pressure,
        input_pair=input_pair,
        input_values=values,
        **props,
    )


def get_pressure_from_altitude(altitude: float, unit_system: UnitSystem) -> float:
    """
    Convert altitude to atmospheric pressure using psychrolib's standard
    atmosphere model.

    Args:
        altitude: Altitude in feet (IP) or meters (SI)
        unit_system: IP or SI

    Returns:
        Atmospheric pressure in psia (IP) or Pa (SI)
    """
    _set_unit_system(unit_system)
    return psychrolib.GetStandardAtmPressure(altitude)
