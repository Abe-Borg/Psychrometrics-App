"""
Airflow and energy calculation engine.

Provides:
  - Airflow/load calculator: solve for Q, CFM, or delta in the standard
    HVAC load equations with altitude-corrected C-factors.
  - Condensation check: compare surface temperature against dew point.

Formulas (IP units at sea level):
  Sensible: Qs = Cs × CFM × ΔT,  Cs = 60 × ρ × cp  ≈ 1.08
  Latent:   Ql = Cl × CFM × ΔW,  Cl = 60 × ρ × hfg ≈ 4760
  Total:    Qt = Ct × CFM × Δh,  Ct = 60 × ρ         ≈ 4.5
"""

import psychrolib

from app.config import UnitSystem
from app.engine.processes.utils import set_unit_system
from app.engine.state_resolver import resolve_state_point
from app.models.airflow import (
    AirflowCalcInput,
    AirflowCalcOutput,
    CalcMode,
    CondensationCheckInput,
    CondensationCheckOutput,
    LoadType,
)

# Psychrometric constants
_CP_IP = 0.244      # BTU/(lb·°F) — specific heat of moist air
_CP_SI = 1006.0     # J/(kg·K)
_HFG_IP = 1061.0    # BTU/lb — latent heat of vaporization
_HFG_SI = 2501000.0 # J/kg

# Default reference conditions when not provided
_DEFAULT_TDB_IP = 70.0    # °F
_DEFAULT_TDB_SI = 21.0    # °C
_DEFAULT_W = 0.01         # lb/lb or kg/kg


def compute_c_factor(
    load_type: LoadType,
    Tdb: float,
    W: float,
    pressure: float,
    unit_system: UnitSystem,
) -> tuple[float, float]:
    """
    Compute the altitude-corrected C constant and air density.

    Returns (C_factor, air_density).
    """
    set_unit_system(unit_system)
    v = psychrolib.GetMoistAirVolume(Tdb, W, pressure)
    rho = 1.0 / v

    if unit_system == UnitSystem.IP:
        if load_type == LoadType.SENSIBLE:
            C = 60.0 * rho * _CP_IP
        elif load_type == LoadType.LATENT:
            C = 60.0 * rho * _HFG_IP
        else:  # TOTAL
            C = 60.0 * rho
    else:
        if load_type == LoadType.SENSIBLE:
            C = rho * _CP_SI       # W per (m³/s) per K
        elif load_type == LoadType.LATENT:
            C = rho * _HFG_SI      # W per (m³/s) per (kg/kg)
        else:  # TOTAL
            C = rho * 1000.0       # W per (m³/s) per (kJ/kg) → factor of 1000 to convert kJ to J

    return (C, rho)


def calculate_airflow(calc_input: AirflowCalcInput) -> AirflowCalcOutput:
    """
    Solve the load equation Q = C × airflow × delta for the unknown variable.
    """
    ci = calc_input

    # Determine reference conditions for C-factor
    if ci.unit_system == UnitSystem.IP:
        ref_Tdb = ci.ref_Tdb if ci.ref_Tdb is not None else _DEFAULT_TDB_IP
    else:
        ref_Tdb = ci.ref_Tdb if ci.ref_Tdb is not None else _DEFAULT_TDB_SI
    ref_W = ci.ref_W if ci.ref_W is not None else _DEFAULT_W

    C, rho = compute_c_factor(ci.load_type, ref_Tdb, ref_W, ci.pressure, ci.unit_system)

    # Solve based on calc_mode
    if ci.calc_mode == CalcMode.SOLVE_Q:
        if ci.airflow is None or ci.delta is None:
            raise ValueError("airflow and delta are required when solving for Q")
        if ci.airflow < 0:
            raise ValueError("airflow must be non-negative")
        Q = C * ci.airflow * ci.delta
        airflow = ci.airflow
        delta = ci.delta

    elif ci.calc_mode == CalcMode.SOLVE_AIRFLOW:
        if ci.Q is None or ci.delta is None:
            raise ValueError("Q and delta are required when solving for airflow")
        if abs(ci.delta) < 1e-12:
            raise ValueError("delta must be non-zero when solving for airflow")
        product = C * ci.delta
        if abs(product) < 1e-12:
            raise ValueError("C × delta is too close to zero")
        airflow = ci.Q / product
        Q = ci.Q
        delta = ci.delta

    elif ci.calc_mode == CalcMode.SOLVE_DELTA:
        if ci.Q is None or ci.airflow is None:
            raise ValueError("Q and airflow are required when solving for delta")
        if ci.airflow <= 0:
            raise ValueError("airflow must be positive when solving for delta")
        product = C * ci.airflow
        if abs(product) < 1e-12:
            raise ValueError("C × airflow is too close to zero")
        delta = ci.Q / product
        Q = ci.Q
        airflow = ci.airflow

    else:
        raise ValueError(f"Unknown calc_mode: {ci.calc_mode}")

    # Build formula string
    formula = _build_formula(ci.load_type, ci.calc_mode, ci.unit_system, C, Q, airflow, delta)

    return AirflowCalcOutput(
        calc_mode=ci.calc_mode,
        load_type=ci.load_type,
        unit_system=ci.unit_system,
        Q=round(Q, 4),
        airflow=round(airflow, 6),
        delta=round(delta, 6),
        C_factor=round(C, 4),
        air_density=round(rho, 6),
        formula=formula,
    )


def check_condensation(ci: CondensationCheckInput) -> CondensationCheckOutput:
    """
    Check whether condensation would occur on a surface.

    Condensation occurs when the surface temperature is below the dew point
    of the surrounding air.
    """
    state = resolve_state_point(
        input_pair=ci.state_pair,
        values=ci.state_values,
        pressure=ci.pressure,
        unit_system=ci.unit_system,
        label="condensation_check",
    )

    dew_point = state.Tdp
    margin = ci.surface_temp - dew_point
    is_condensing = ci.surface_temp < dew_point

    return CondensationCheckOutput(
        is_condensing=is_condensing,
        surface_temp=round(ci.surface_temp, 2),
        dew_point=round(dew_point, 2),
        margin=round(margin, 2),
        unit_system=ci.unit_system,
    )


def _build_formula(
    load_type: LoadType,
    calc_mode: CalcMode,
    unit_system: UnitSystem,
    C: float,
    Q: float,
    airflow: float,
    delta: float,
) -> str:
    """Build a human-readable formula string showing the calculation."""
    is_ip = unit_system == UnitSystem.IP

    # Variable names
    if load_type == LoadType.SENSIBLE:
        q_name = "Qs"
        delta_name = "\u0394T"
        delta_unit = "\u00b0F" if is_ip else "\u00b0C"
    elif load_type == LoadType.LATENT:
        q_name = "Ql"
        delta_name = "\u0394W"
        delta_unit = "lb/lb" if is_ip else "kg/kg"
    else:
        q_name = "Qt"
        delta_name = "\u0394h"
        delta_unit = "BTU/lb" if is_ip else "kJ/kg"

    q_unit = "BTU/hr" if is_ip else "W"
    airflow_unit = "CFM" if is_ip else "m\u00b3/s"

    C_str = f"{C:.4g}"
    Q_str = f"{Q:,.2f}"
    airflow_str = f"{airflow:,.2f}"
    delta_str = f"{delta:.4g}"

    if calc_mode == CalcMode.SOLVE_Q:
        return f"{q_name} = {C_str} \u00d7 {airflow_str} {airflow_unit} \u00d7 {delta_str} {delta_unit} = {Q_str} {q_unit}"
    elif calc_mode == CalcMode.SOLVE_AIRFLOW:
        return f"{airflow_unit} = {Q_str} {q_unit} / ({C_str} \u00d7 {delta_str} {delta_unit}) = {airflow_str} {airflow_unit}"
    else:  # SOLVE_DELTA
        return f"{delta_name} = {Q_str} {q_unit} / ({C_str} \u00d7 {airflow_str} {airflow_unit}) = {delta_str} {delta_unit}"
