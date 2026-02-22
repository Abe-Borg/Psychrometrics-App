"""
Humidification process solvers: steam, adiabatic, and heated water spray.

Steam humidification:
    Constant dry-bulb temperature (vertical path on psychrometric chart).
    Moisture is added via steam injection; the air's Tdb stays nearly constant.

Adiabatic humidification:
    Constant wet-bulb temperature (curved diagonal toward saturation).
    Water evaporates using sensible heat from the air (e.g., wetted media).
    Effectiveness ε = (Tdb_in - Tdb_out) / (Tdb_in - Twb_in).

Heated water spray humidification:
    Air moves in a straight line toward the saturation point at the water
    temperature.  When water_temp == Twb, this degenerates to adiabatic.
    When water_temp >> Tdb, both Tdb and W increase (steam-like but not vertical).
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
    HumidificationMode,
    PathPoint,
)


def _set_unit_system(unit_system: UnitSystem) -> None:
    if unit_system == UnitSystem.IP:
        psychrolib.SetUnitSystem(psychrolib.IP)
    else:
        psychrolib.SetUnitSystem(psychrolib.SI)


def _w_display(W: float, unit_system: UnitSystem) -> float:
    """Convert humidity ratio to display units (grains/lb or g/kg)."""
    if unit_system == UnitSystem.IP:
        return round(W * GRAINS_PER_LB, 4)
    else:
        return round(W * 1000.0, 4)


# ---------------------------------------------------------------------------
# Steam humidification — constant Tdb (vertical line)
# ---------------------------------------------------------------------------

class SteamHumidificationSolver(ProcessSolver):
    """Solver for steam humidification (constant dry-bulb temperature)."""

    def solve(self, process_input: ProcessInput) -> ProcessOutput:
        pi = process_input
        mode = pi.humidification_mode
        if mode is None:
            raise ValueError(
                "humidification_mode is required for steam humidification"
            )

        _set_unit_system(pi.unit_system)

        # Resolve start state
        start = resolve_state_point(
            input_pair=pi.start_point_pair,
            values=pi.start_point_values,
            pressure=pi.pressure,
            unit_system=pi.unit_system,
            label="start",
        )

        warnings: list[str] = []

        # Determine end humidity ratio
        if mode == HumidificationMode.TARGET_RH:
            if pi.target_RH is None:
                raise ValueError("target_RH is required for target_rh mode")
            if pi.target_RH <= 0 or pi.target_RH > 100:
                raise ValueError("target_RH must be between 0 and 100")
            # Resolve at same Tdb with target RH to find the end W
            end = resolve_state_point(
                input_pair=("Tdb", "RH"),
                values=(start.Tdb, pi.target_RH),
                pressure=pi.pressure,
                unit_system=pi.unit_system,
                label="end",
            )

        elif mode == HumidificationMode.TARGET_W:
            if pi.target_W is None:
                raise ValueError("target_W is required for target_w mode")
            if pi.target_W < 0:
                raise ValueError("target_W must be non-negative")
            end = resolve_state_point(
                input_pair=("Tdb", "W"),
                values=(start.Tdb, pi.target_W),
                pressure=pi.pressure,
                unit_system=pi.unit_system,
                label="end",
            )

        else:
            raise ValueError(
                f"Unsupported humidification_mode '{mode}' for steam humidification. "
                f"Use 'target_rh' or 'target_w'."
            )

        # Validate direction (humidification = W increases)
        if end.W < start.W:
            warnings.append(
                f"End humidity ratio ({end.W:.6f}) is lower than start ({start.W:.6f}). "
                f"This is dehumidification, not humidification."
            )

        # Check supersaturation (RH > 100 is unreachable in practice)
        W_sat = psychrolib.GetSatHumRatio(start.Tdb, pi.pressure)
        if end.W > W_sat * 1.001:
            warnings.append(
                f"Target humidity ratio exceeds saturation at Tdb={start.Tdb:.1f}. "
                f"Fog/condensation would occur."
            )

        # Path: vertical line (constant Tdb)
        n_points = 12
        path_points = []
        for i in range(n_points + 1):
            t = i / n_points
            W_i = start.W + t * (end.W - start.W)
            path_points.append(PathPoint(
                Tdb=round(start.Tdb, 4),
                W=round(W_i, 7),
                W_display=_w_display(W_i, pi.unit_system),
            ))

        delta_W = end.W - start.W
        delta_h = end.h - start.h

        metadata = {
            "delta_W": round(delta_W, 7),
            "delta_W_display": _w_display(delta_W, pi.unit_system),
            "delta_h": round(delta_h, 4),
            "start_RH": round(start.RH, 2),
            "end_RH": round(end.RH, 2),
        }

        return ProcessOutput(
            process_type=ProcessType.STEAM_HUMIDIFICATION,
            unit_system=pi.unit_system,
            pressure=pi.pressure,
            start_point=start.model_dump(),
            end_point=end.model_dump(),
            path_points=path_points,
            metadata=metadata,
            warnings=warnings,
        )


# ---------------------------------------------------------------------------
# Adiabatic humidification — constant Twb (curved diagonal)
# ---------------------------------------------------------------------------

class AdiabaticHumidificationSolver(ProcessSolver):
    """Solver for adiabatic humidification (constant wet-bulb temperature)."""

    def solve(self, process_input: ProcessInput) -> ProcessOutput:
        pi = process_input
        mode = pi.humidification_mode
        if mode is None:
            raise ValueError(
                "humidification_mode is required for adiabatic humidification"
            )

        _set_unit_system(pi.unit_system)

        # Resolve start state
        start = resolve_state_point(
            input_pair=pi.start_point_pair,
            values=pi.start_point_values,
            pressure=pi.pressure,
            unit_system=pi.unit_system,
            label="start",
        )

        warnings: list[str] = []
        Twb = start.Twb

        # Saturation state at the entering Twb (100% effectiveness target)
        sat_at_Twb = resolve_state_point(
            input_pair=("Tdb", "RH"),
            values=(Twb, 100.0),
            pressure=pi.pressure,
            unit_system=pi.unit_system,
            label="sat_at_Twb",
        )

        if mode == HumidificationMode.EFFECTIVENESS:
            if pi.effectiveness is None:
                raise ValueError("effectiveness is required for effectiveness mode")
            eff = pi.effectiveness
            if eff < 0 or eff > 1:
                raise ValueError(
                    f"effectiveness must be between 0 and 1, got {eff}"
                )

            # End Tdb via effectiveness definition
            end_Tdb = start.Tdb - eff * (start.Tdb - Twb)

        elif mode == HumidificationMode.TARGET_RH:
            if pi.target_RH is None:
                raise ValueError("target_RH is required for target_rh mode")
            if pi.target_RH <= start.RH:
                raise ValueError(
                    f"target_RH ({pi.target_RH}%) must be greater than "
                    f"current RH ({start.RH:.1f}%)"
                )
            if pi.target_RH > 100:
                raise ValueError("target_RH cannot exceed 100%")

            # Find Tdb along constant-Twb line where RH = target
            target_rh_frac = pi.target_RH / 100.0

            def objective(Tdb: float) -> float:
                W_i = psychrolib.GetHumRatioFromTWetBulb(Tdb, Twb, pi.pressure)
                W_sat_i = psychrolib.GetSatHumRatio(Tdb, pi.pressure)
                rh_i = W_i / W_sat_i if W_sat_i > 0 else 0.0
                return rh_i - target_rh_frac

            # Search between current Tdb (lower RH) and Twb (100% RH)
            end_Tdb = brentq(objective, Twb, start.Tdb, xtol=1e-6)

            # Compute effective effectiveness for metadata
            eff = (start.Tdb - end_Tdb) / (start.Tdb - Twb) if abs(start.Tdb - Twb) > 1e-10 else 1.0

        else:
            raise ValueError(
                f"Unsupported humidification_mode '{mode}' for adiabatic humidification. "
                f"Use 'effectiveness' or 'target_rh'."
            )

        # Resolve end state along constant Twb
        end_W = psychrolib.GetHumRatioFromTWetBulb(end_Tdb, Twb, pi.pressure)
        end = resolve_state_point(
            input_pair=("Tdb", "W"),
            values=(end_Tdb, end_W),
            pressure=pi.pressure,
            unit_system=pi.unit_system,
            label="end",
        )

        # Path: follow constant Twb curve (slightly curved, not a straight line)
        n_points = 20  # more points for curved path
        path_points = []
        for i in range(n_points + 1):
            t = i / n_points
            Tdb_i = start.Tdb + t * (end_Tdb - start.Tdb)
            W_i = psychrolib.GetHumRatioFromTWetBulb(Tdb_i, Twb, pi.pressure)
            path_points.append(PathPoint(
                Tdb=round(Tdb_i, 4),
                W=round(W_i, 7),
                W_display=_w_display(W_i, pi.unit_system),
            ))

        delta_W = end.W - start.W
        delta_Tdb = end.Tdb - start.Tdb

        metadata = {
            "effectiveness": round(eff, 4),
            "Twb": round(Twb, 4),
            "delta_Tdb": round(delta_Tdb, 4),
            "delta_W": round(delta_W, 7),
            "delta_W_display": _w_display(delta_W, pi.unit_system),
            "start_RH": round(start.RH, 2),
            "end_RH": round(end.RH, 2),
        }

        return ProcessOutput(
            process_type=ProcessType.ADIABATIC_HUMIDIFICATION,
            unit_system=pi.unit_system,
            pressure=pi.pressure,
            start_point=start.model_dump(),
            end_point=end.model_dump(),
            path_points=path_points,
            metadata=metadata,
            warnings=warnings,
        )


# ---------------------------------------------------------------------------
# Heated water spray humidification — straight line toward saturation at T_water
# ---------------------------------------------------------------------------

class HeatedWaterHumidificationSolver(ProcessSolver):
    """Solver for heated water spray humidification.

    Air moves in a straight line toward the saturation point at the spray
    water temperature. Effectiveness determines how far along that line
    the leaving air ends up.
    """

    def solve(self, process_input: ProcessInput) -> ProcessOutput:
        pi = process_input

        if pi.effectiveness is None:
            raise ValueError(
                "effectiveness is required for heated water humidification"
            )
        if pi.water_temperature is None:
            raise ValueError(
                "water_temperature is required for heated water humidification"
            )

        eff = pi.effectiveness
        if eff < 0 or eff > 1:
            raise ValueError(
                f"effectiveness must be between 0 and 1, got {eff}"
            )

        _set_unit_system(pi.unit_system)

        # Resolve start state
        start = resolve_state_point(
            input_pair=pi.start_point_pair,
            values=pi.start_point_values,
            pressure=pi.pressure,
            unit_system=pi.unit_system,
            label="start",
        )

        # Saturation state at the water temperature
        sat_water = resolve_state_point(
            input_pair=("Tdb", "RH"),
            values=(pi.water_temperature, 100.0),
            pressure=pi.pressure,
            unit_system=pi.unit_system,
            label="sat_water",
        )

        warnings: list[str] = []

        # End state: linear interpolation toward saturation at water temp
        end_Tdb = start.Tdb + eff * (sat_water.Tdb - start.Tdb)
        end_W = start.W + eff * (sat_water.W - start.W)

        end = resolve_state_point(
            input_pair=("Tdb", "W"),
            values=(end_Tdb, end_W),
            pressure=pi.pressure,
            unit_system=pi.unit_system,
            label="end",
        )

        # Check if moisture actually increases
        if end.W < start.W:
            warnings.append(
                "End humidity ratio is lower than start. "
                "The water temperature may be too cold for humidification."
            )

        # Path: straight line from start to end
        n_points = 12
        path_points = []
        for i in range(n_points + 1):
            t = i / n_points
            Tdb_i = start.Tdb + t * (end_Tdb - start.Tdb)
            W_i = start.W + t * (end_W - start.W)
            path_points.append(PathPoint(
                Tdb=round(Tdb_i, 4),
                W=round(W_i, 7),
                W_display=_w_display(W_i, pi.unit_system),
            ))

        delta_W = end.W - start.W
        delta_Tdb = end.Tdb - start.Tdb
        delta_h = end.h - start.h

        metadata = {
            "effectiveness": round(eff, 4),
            "water_temperature": round(pi.water_temperature, 4),
            "sat_water_Tdb": round(sat_water.Tdb, 4),
            "sat_water_W": round(sat_water.W, 7),
            "sat_water_W_display": _w_display(sat_water.W, pi.unit_system),
            "delta_Tdb": round(delta_Tdb, 4),
            "delta_W": round(delta_W, 7),
            "delta_W_display": _w_display(delta_W, pi.unit_system),
            "delta_h": round(delta_h, 4),
            "start_RH": round(start.RH, 2),
            "end_RH": round(end.RH, 2),
        }

        return ProcessOutput(
            process_type=ProcessType.HEATED_WATER_HUMIDIFICATION,
            unit_system=pi.unit_system,
            pressure=pi.pressure,
            start_point=start.model_dump(),
            end_point=end.model_dump(),
            path_points=path_points,
            metadata=metadata,
            warnings=warnings,
        )
