"""
Chemical (desiccant) dehumidification process solver.

In a desiccant dehumidification process, air passes through a desiccant
medium (silica gel, lithium chloride, molecular sieve, etc.) that adsorbs
moisture.  The heat of adsorption raises the air temperature.

The process approximately follows a constant-enthalpy line on the
psychrometric chart: as W decreases, Tdb increases such that h stays
roughly constant.

Two modes:
  - TARGET_W:  Given start + target humidity ratio
  - TARGET_RH: Given start + target relative humidity (solved iteratively)
"""

import psychrolib
from scipy.optimize import brentq

from app.config import UnitSystem, GRAINS_PER_LB
from app.engine.state_resolver import resolve_state_point
from app.engine.processes.base import ProcessSolver
from app.models.process import (
    ProcessInput,
    ProcessOutput,
    ProcessType,
    DehumidificationMode,
    PathPoint,
)


def _set_unit_system(unit_system: UnitSystem) -> None:
    if unit_system == UnitSystem.IP:
        psychrolib.SetUnitSystem(psychrolib.IP)
    else:
        psychrolib.SetUnitSystem(psychrolib.SI)


def _w_display(W: float, unit_system: UnitSystem) -> float:
    if unit_system == UnitSystem.IP:
        return round(W * GRAINS_PER_LB, 4)
    else:
        return round(W * 1000.0, 4)


class ChemicalDehumSolver(ProcessSolver):
    """Solver for chemical/desiccant dehumidification (approximately constant h)."""

    def solve(self, process_input: ProcessInput) -> ProcessOutput:
        pi = process_input
        mode = pi.dehum_mode

        if mode is None:
            raise ValueError(
                "dehum_mode is required for chemical dehumidification"
            )

        _set_unit_system(pi.unit_system)

        start = resolve_state_point(
            input_pair=pi.start_point_pair,
            values=pi.start_point_values,
            pressure=pi.pressure,
            unit_system=pi.unit_system,
            label="start",
        )

        warnings: list[str] = []
        h_start = start.h

        if mode == DehumidificationMode.TARGET_W:
            if pi.target_W is None:
                raise ValueError("target_W is required for target_w mode")
            end_W = pi.target_W
            if end_W < 0:
                raise ValueError("target_W must be non-negative")

        elif mode == DehumidificationMode.TARGET_RH:
            if pi.target_RH is None:
                raise ValueError("target_RH is required for target_rh mode")
            if pi.target_RH <= 0 or pi.target_RH > 100:
                raise ValueError("target_RH must be between 0 and 100")

            # Find W where, at constant h, RH equals the target.
            # As W decreases (dehum), Tdb rises, and RH drops.
            target_rh_frac = pi.target_RH / 100.0

            def objective(W: float) -> float:
                Tdb_i = psychrolib.GetTDryBulbFromEnthalpyAndHumRatio(h_start, W)
                W_sat_i = psychrolib.GetSatHumRatio(Tdb_i, pi.pressure)
                rh_i = W / W_sat_i if W_sat_i > 0 else 0.0
                return rh_i - target_rh_frac

            # Search: W from near-zero to start.W
            # At W = start.W: RH = start.RH (should be above target for dehum)
            # At W → 0: Tdb is high, RH → 0
            W_lo = 1e-6
            W_hi = start.W

            f_lo = objective(W_lo)
            f_hi = objective(W_hi)
            if f_lo * f_hi > 0:
                raise ValueError(
                    f"Cannot reach target RH {pi.target_RH}% via constant-enthalpy "
                    f"dehumidification from current conditions "
                    f"(RH={start.RH:.1f}%)."
                )

            end_W = brentq(objective, W_lo, W_hi, xtol=1e-8)

        else:
            raise ValueError(f"Unknown dehum_mode: {mode}")

        # Validate: dehumidification = W decreases
        if end_W > start.W:
            warnings.append(
                f"Target W ({end_W:.6f}) is higher than start ({start.W:.6f}). "
                f"This is humidification, not dehumidification."
            )

        # Compute end Tdb from constant enthalpy
        end_Tdb = psychrolib.GetTDryBulbFromEnthalpyAndHumRatio(h_start, end_W)

        end = resolve_state_point(
            input_pair=("Tdb", "W"),
            values=(end_Tdb, end_W),
            pressure=pi.pressure,
            unit_system=pi.unit_system,
            label="end",
        )

        # Path: sweep W from start to end at constant h (slightly curved)
        n_points = 16
        path_points = []
        for i in range(n_points + 1):
            t = i / n_points
            W_i = start.W + t * (end_W - start.W)
            Tdb_i = psychrolib.GetTDryBulbFromEnthalpyAndHumRatio(h_start, W_i)
            path_points.append(PathPoint(
                Tdb=round(Tdb_i, 4),
                W=round(W_i, 7),
                W_display=_w_display(W_i, pi.unit_system),
            ))

        delta_W = end.W - start.W
        delta_Tdb = end.Tdb - start.Tdb

        metadata = {
            "h_constant": round(h_start, 4),
            "delta_Tdb": round(delta_Tdb, 4),
            "delta_W": round(delta_W, 7),
            "delta_W_display": _w_display(delta_W, pi.unit_system),
            "start_RH": round(start.RH, 2),
            "end_RH": round(end.RH, 2),
        }

        return ProcessOutput(
            process_type=ProcessType.CHEMICAL_DEHUMIDIFICATION,
            unit_system=pi.unit_system,
            pressure=pi.pressure,
            start_point=start.model_dump(),
            end_point=end.model_dump(),
            path_points=path_points,
            metadata=metadata,
            warnings=warnings,
        )
