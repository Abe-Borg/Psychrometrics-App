"""
Coil analysis engine.

Provides forward and reverse coil analysis with full load breakdown
and optional GPM estimation. Reuses shared utility functions from
the process solver framework.

Forward mode: entering conditions + ADP + BF → leaving conditions + loads
Reverse mode: entering + leaving conditions → ADP + BF + loads
"""

from app.config import UnitSystem
from app.engine.state_resolver import resolve_state_point
from app.engine.processes.utils import (
    set_unit_system,
    w_display,
    find_adp,
    generate_path_points,
)
from app.models.coil import CoilInput, CoilOutput, CoilMode
from app.models.process import PathPoint


def analyze_coil(coil_input: CoilInput) -> CoilOutput:
    """Main entry point: dispatch to forward or reverse coil analysis."""
    ci = coil_input

    # Resolve the entering state
    entering = resolve_state_point(
        input_pair=ci.entering_pair,
        values=ci.entering_values,
        pressure=ci.pressure,
        unit_system=ci.unit_system,
        label="entering",
    )

    warnings: list[str] = []

    if ci.mode == CoilMode.FORWARD:
        return _forward_coil(ci, entering, warnings)
    elif ci.mode == CoilMode.REVERSE:
        return _reverse_coil(ci, entering, warnings)
    else:
        raise ValueError(f"Unknown coil mode: {ci.mode}")


def _forward_coil(ci: CoilInput, entering, warnings: list[str]) -> CoilOutput:
    """Forward mode: ADP + BF → leaving state, loads, optional GPM."""
    if ci.adp_Tdb is None or ci.bypass_factor is None:
        raise ValueError("adp_Tdb and bypass_factor are required for forward mode")

    BF = ci.bypass_factor
    if not (0.0 < BF < 1.0):
        raise ValueError("bypass_factor must be between 0 and 1 (exclusive)")

    # Resolve ADP as a saturated state (100% RH)
    set_unit_system(ci.unit_system)
    adp = resolve_state_point(
        input_pair=("Tdb", "RH"),
        values=(ci.adp_Tdb, 100.0),
        pressure=ci.pressure,
        unit_system=ci.unit_system,
        label="ADP",
    )

    # Validate: ADP should be below the entering dew point for dehumidification
    if ci.adp_Tdb >= entering.Tdp:
        warnings.append(
            f"ADP Tdb ({ci.adp_Tdb:.1f}) is at or above the entering dew point "
            f"({entering.Tdp:.1f}). No dehumidification would occur."
        )

    # Leaving conditions via bypass factor
    leaving_Tdb = adp.Tdb + BF * (entering.Tdb - adp.Tdb)
    leaving_W = adp.W + BF * (entering.W - adp.W)

    # Resolve full leaving state
    leaving = resolve_state_point(
        input_pair=("Tdb", "W"),
        values=(leaving_Tdb, leaving_W),
        pressure=ci.pressure,
        unit_system=ci.unit_system,
        label="leaving",
    )

    CF = 1.0 - BF

    # Compute loads and build output
    loads = _compute_loads(entering, leaving, ci.unit_system, ci.airflow)
    gpm = _estimate_gpm(
        loads["Qt"], ci.airflow, ci.water_entering_temp, ci.water_leaving_temp,
        ci.unit_system,
    )

    path_points = generate_path_points(
        entering.Tdb, entering.W, leaving.Tdb, leaving.W, ci.unit_system
    )

    return CoilOutput(
        unit_system=ci.unit_system,
        pressure=ci.pressure,
        mode=CoilMode.FORWARD,
        entering=entering.model_dump(),
        leaving=leaving.model_dump(),
        adp=adp.model_dump(),
        bypass_factor=round(BF, 4),
        contact_factor=round(CF, 4),
        Qs=loads["Qs"],
        Ql=loads["Ql"],
        Qt=loads["Qt"],
        SHR=loads["SHR"],
        load_unit=loads["load_unit"],
        gpm=gpm,
        path_points=path_points,
        warnings=warnings,
    )


def _reverse_coil(ci: CoilInput, entering, warnings: list[str]) -> CoilOutput:
    """Reverse mode: entering + leaving → ADP, BF, loads, optional GPM."""
    if ci.leaving_pair is None or ci.leaving_values is None:
        raise ValueError("leaving_pair and leaving_values are required for reverse mode")

    # Resolve the leaving state
    leaving = resolve_state_point(
        input_pair=ci.leaving_pair,
        values=ci.leaving_values,
        pressure=ci.pressure,
        unit_system=ci.unit_system,
        label="leaving",
    )

    # Validate: leaving should have lower Tdb than entering
    if leaving.Tdb >= entering.Tdb:
        raise ValueError(
            f"Leaving Tdb ({leaving.Tdb:.1f}) must be less than entering Tdb ({entering.Tdb:.1f})"
        )
    if leaving.W >= entering.W:
        warnings.append(
            f"Leaving humidity ratio ({leaving.W:.6f}) is not less than entering ({entering.W:.6f}). "
            f"This looks like sensible cooling only, not cooling & dehumidification."
        )

    # Find the ADP
    set_unit_system(ci.unit_system)
    adp_Tdb = find_adp(
        entering.Tdb, entering.W, leaving.Tdb, leaving.W,
        ci.pressure, ci.unit_system,
    )

    # Resolve full ADP state
    adp = resolve_state_point(
        input_pair=("Tdb", "RH"),
        values=(adp_Tdb, 100.0),
        pressure=ci.pressure,
        unit_system=ci.unit_system,
        label="ADP",
    )

    # Compute BF
    denom = entering.Tdb - adp.Tdb
    if abs(denom) < 1e-10:
        raise ValueError("Entering Tdb equals ADP Tdb — cannot compute bypass factor")

    BF = (leaving.Tdb - adp.Tdb) / denom
    CF = 1.0 - BF

    if BF < 0 or BF > 1:
        raise ValueError(
            f"Computed bypass factor ({BF:.4f}) is out of range (0-1). "
            f"The leaving state may be beyond the ADP."
        )

    # Compute loads and build output
    loads = _compute_loads(entering, leaving, ci.unit_system, ci.airflow)
    gpm = _estimate_gpm(
        loads["Qt"], ci.airflow, ci.water_entering_temp, ci.water_leaving_temp,
        ci.unit_system,
    )

    path_points = generate_path_points(
        entering.Tdb, entering.W, leaving.Tdb, leaving.W, ci.unit_system
    )

    return CoilOutput(
        unit_system=ci.unit_system,
        pressure=ci.pressure,
        mode=CoilMode.REVERSE,
        entering=entering.model_dump(),
        leaving=leaving.model_dump(),
        adp=adp.model_dump(),
        bypass_factor=round(BF, 4),
        contact_factor=round(CF, 4),
        Qs=loads["Qs"],
        Ql=loads["Ql"],
        Qt=loads["Qt"],
        SHR=loads["SHR"],
        load_unit=loads["load_unit"],
        gpm=gpm,
        path_points=path_points,
        warnings=warnings,
    )


def _compute_loads(entering, leaving, unit_system: UnitSystem, airflow: float | None) -> dict:
    """
    Compute sensible, latent, and total loads.

    If airflow is provided, returns absolute loads (BTU/hr or W).
    Otherwise, returns loads per unit mass of dry air (BTU/lb or kJ/kg).
    """
    if unit_system == UnitSystem.IP:
        cp = 0.244  # BTU/(lb·°F)
    else:
        cp = 1.006  # kJ/(kg·K)

    # Per-unit-mass loads
    Qs_mass = cp * (entering.Tdb - leaving.Tdb)
    Qt_mass = entering.h - leaving.h
    Ql_mass = Qt_mass - Qs_mass
    SHR = Qs_mass / Qt_mass if abs(Qt_mass) > 1e-10 else 1.0

    if airflow is not None and airflow > 0:
        # Convert to absolute loads
        if unit_system == UnitSystem.IP:
            # C_sensible = 60 × ρ × cp ≈ 1.08 at sea level
            # Use actual density: ρ = 1/v
            rho = 1.0 / entering.v  # lb/ft³
            C = 60.0 * rho * cp
            Qs = C * airflow * (entering.Tdb - leaving.Tdb)
            Qt = 4.5 * airflow * (entering.h - leaving.h)
            Ql = Qt - Qs
            load_unit = "BTU/hr"
        else:
            # SI: airflow in m³/s, ρ = 1/v (kg/m³)
            rho = 1.0 / entering.v
            mass_flow = rho * airflow  # kg/s
            Qs = mass_flow * cp * (entering.Tdb - leaving.Tdb) * 1000  # W
            Qt = mass_flow * (entering.h - leaving.h) * 1000  # W
            Ql = Qt - Qs
            load_unit = "W"
    else:
        Qs = Qs_mass
        Ql = Ql_mass
        Qt = Qt_mass
        load_unit = "BTU/lb" if unit_system == UnitSystem.IP else "kJ/kg"

    return {
        "Qs": round(Qs, 2),
        "Ql": round(Ql, 2),
        "Qt": round(Qt, 2),
        "SHR": round(SHR, 4),
        "load_unit": load_unit,
    }


def _estimate_gpm(
    Qt: float,
    airflow: float | None,
    water_entering_temp: float | None,
    water_leaving_temp: float | None,
    unit_system: UnitSystem,
) -> float | None:
    """
    Estimate water flow rate from total load and water temperatures.

    IP: GPM = Qt (BTU/hr) / (500 × ΔT_water)
        where 500 = 60 min/hr × 8.33 lb/gal × 1 BTU/(lb·°F)
    SI: L/s = Qt (W) / (4186 × ΔT_water)
        where 4186 = specific heat of water in J/(kg·K) × 1 kg/L

    Returns None if water temps not provided or Qt is not absolute (no airflow).
    """
    if water_entering_temp is None or water_leaving_temp is None:
        return None
    if airflow is None or airflow <= 0:
        return None

    delta_T_water = abs(water_leaving_temp - water_entering_temp)
    if delta_T_water < 0.01:
        return None

    if unit_system == UnitSystem.IP:
        gpm = Qt / (500.0 * delta_T_water)
    else:
        liters_per_sec = Qt / (4186.0 * delta_T_water)
        gpm = liters_per_sec  # stored as L/s for SI

    return round(gpm, 2)
