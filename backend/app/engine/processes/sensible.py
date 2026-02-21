"""
Sensible heating and cooling process solver.

A sensible process is a horizontal line on the psychrometric chart — the humidity
ratio (W) stays constant while the dry-bulb temperature changes.

Three input modes:
  - TARGET_TDB: user provides the desired leaving dry-bulb
  - DELTA_T: user provides a temperature difference (positive = heating, negative = cooling)
  - HEAT_AND_AIRFLOW: user provides sensible heat (BTU/hr or W) and airflow (CFM or m³/s),
    and we compute ΔT = Q / (C_factor × airflow)
"""

import psychrolib

from app.config import UnitSystem, GRAINS_PER_LB
from app.engine.state_resolver import resolve_state_point
from app.engine.processes.base import ProcessSolver
from app.models.process import (
    ProcessInput,
    ProcessOutput,
    ProcessType,
    SensibleMode,
    PathPoint,
)


def _set_unit_system(unit_system: UnitSystem) -> None:
    if unit_system == UnitSystem.IP:
        psychrolib.SetUnitSystem(psychrolib.IP)
    else:
        psychrolib.SetUnitSystem(psychrolib.SI)


class SensibleSolver(ProcessSolver):
    """Solver for sensible heating and cooling processes."""

    def solve(self, process_input: ProcessInput) -> ProcessOutput:
        pi = process_input
        mode = pi.sensible_mode

        if mode is None:
            raise ValueError("sensible_mode is required for sensible heating/cooling")

        # Resolve the start state
        start = resolve_state_point(
            input_pair=pi.start_point_pair,
            values=pi.start_point_values,
            pressure=pi.pressure,
            unit_system=pi.unit_system,
            label="start",
        )

        start_Tdb = start.Tdb
        start_W = start.W
        warnings: list[str] = []

        # Determine end Tdb based on mode
        if mode == SensibleMode.TARGET_TDB:
            if pi.target_Tdb is None:
                raise ValueError("target_Tdb is required for TARGET_TDB mode")
            end_Tdb = pi.target_Tdb

        elif mode == SensibleMode.DELTA_T:
            if pi.delta_T is None:
                raise ValueError("delta_T is required for DELTA_T mode")
            end_Tdb = start_Tdb + pi.delta_T

        elif mode == SensibleMode.HEAT_AND_AIRFLOW:
            if pi.Q_sensible is None or pi.airflow_cfm is None:
                raise ValueError(
                    "Q_sensible and airflow_cfm are required for HEAT_AND_AIRFLOW mode"
                )
            if pi.airflow_cfm <= 0:
                raise ValueError("airflow_cfm must be positive")

            # Compute the altitude-corrected C factor
            # C = 60 × ρ × cp, where ρ = 1/v (density from specific volume)
            # cp of moist air ≈ 0.244 BTU/(lb·°F) for IP, 1.006 kJ/(kg·K) for SI
            _set_unit_system(pi.unit_system)
            v = psychrolib.GetMoistAirVolume(start_Tdb, start_W, pi.pressure)
            rho = 1.0 / v  # lb/ft³ (IP) or kg/m³ (SI)

            if pi.unit_system == UnitSystem.IP:
                cp = 0.244  # BTU/(lb·°F)
                C_factor = 60.0 * rho * cp  # BTU/(hr·CFM·°F) — the "1.08" at sea level
                # ΔT = Q / (C × CFM), Q in BTU/hr
                delta_T = pi.Q_sensible / (C_factor * pi.airflow_cfm)
            else:
                cp = 1006.0  # J/(kg·K)
                # For SI: Q in W, airflow in m³/s
                # ΔT = Q / (ρ × cp × airflow)
                delta_T = pi.Q_sensible / (rho * cp * pi.airflow_cfm)

            end_Tdb = start_Tdb + delta_T
        else:
            raise ValueError(f"Unknown sensible mode: {mode}")

        # Determine process type from direction
        actual_type = (
            ProcessType.SENSIBLE_HEATING
            if end_Tdb >= start_Tdb
            else ProcessType.SENSIBLE_COOLING
        )

        # Check if cooling crosses the dew point
        if end_Tdb < start.Tdp:
            warnings.append(
                f"Target Tdb ({end_Tdb:.1f}) is below the dew point ({start.Tdp:.1f}). "
                f"In practice, dehumidification would occur. "
                f"Consider using a cooling & dehumidification process."
            )

        # Resolve end state at same W (sensible = constant humidity ratio)
        end = resolve_state_point(
            input_pair=("Tdb", "W"),
            values=(end_Tdb, start_W),
            pressure=pi.pressure,
            unit_system=pi.unit_system,
            label="end",
        )

        # Path: just start and end (horizontal line)
        if pi.unit_system == UnitSystem.IP:
            start_W_display = start_W * GRAINS_PER_LB
            end_W_display = start_W * GRAINS_PER_LB
        else:
            start_W_display = start_W * 1000.0
            end_W_display = start_W * 1000.0

        path_points = [
            PathPoint(Tdb=start_Tdb, W=start_W, W_display=round(start_W_display, 4)),
            PathPoint(Tdb=end_Tdb, W=start_W, W_display=round(end_W_display, 4)),
        ]

        # Metadata
        delta_T_actual = end_Tdb - start_Tdb
        Qs_per_lb = end.h - start.h  # enthalpy difference per lb (or kg) of dry air

        metadata: dict = {
            "delta_T": round(delta_T_actual, 4),
            "Qs_per_unit_mass": round(Qs_per_lb, 4),
        }

        if mode == SensibleMode.HEAT_AND_AIRFLOW:
            metadata["Q_sensible"] = pi.Q_sensible
            metadata["airflow"] = pi.airflow_cfm
            metadata["C_factor"] = round(C_factor, 4)

        return ProcessOutput(
            process_type=actual_type,
            unit_system=pi.unit_system,
            pressure=pi.pressure,
            start_point=start.model_dump(),
            end_point=end.model_dump(),
            path_points=path_points,
            metadata=metadata,
            warnings=warnings,
        )
