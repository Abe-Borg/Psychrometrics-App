"""
Evaporative cooling process solvers: direct, indirect, and indirect-direct two-stage.

Direct evaporative cooling (DEC):
    Air passes through a wetted media pad.  The process follows a constant
    wet-bulb line toward saturation — identical physics to adiabatic
    humidification, but framed as a cooling process.
    Effectiveness ε = (Tdb_in - Tdb_out) / (Tdb_in - Twb_in).

Indirect evaporative cooling (IEC):
    Primary air is sensibly cooled (constant W, horizontal path) via a heat
    exchanger whose secondary side uses evaporative cooling.  The theoretical
    limit is the secondary air's wet-bulb temperature.
    Effectiveness ε = (Tdb_in - Tdb_out) / (Tdb_in - Twb_secondary).
    If no secondary air is specified, it defaults to the primary entering air.

Indirect-direct two-stage (IDEC):
    Stage 1: IEC (horizontal) followed by Stage 2: DEC (diagonal along Twb).
    Each stage has its own effectiveness.
"""

import psychrolib

from app.config import UnitSystem, GRAINS_PER_LB
from app.engine.state_resolver import resolve_state_point
from app.engine.processes.base import ProcessSolver
from app.models.process import (
    ProcessInput,
    ProcessOutput,
    ProcessType,
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


def _generate_constant_twb_path(
    start_Tdb: float,
    end_Tdb: float,
    Twb: float,
    pressure: float,
    unit_system: UnitSystem,
    n_points: int = 20,
) -> list[PathPoint]:
    """Generate path points along a constant wet-bulb line."""
    _set_unit_system(unit_system)
    points = []
    for i in range(n_points + 1):
        t = i / n_points
        Tdb_i = start_Tdb + t * (end_Tdb - start_Tdb)
        W_i = psychrolib.GetHumRatioFromTWetBulb(Tdb_i, Twb, pressure)
        points.append(PathPoint(
            Tdb=round(Tdb_i, 4),
            W=round(W_i, 7),
            W_display=_w_display(W_i, unit_system),
        ))
    return points


def _generate_horizontal_path(
    start_Tdb: float,
    end_Tdb: float,
    W: float,
    unit_system: UnitSystem,
    n_points: int = 2,
) -> list[PathPoint]:
    """Generate path points along a horizontal (constant W) line."""
    points = []
    for i in range(n_points):
        t = i / max(n_points - 1, 1)
        Tdb_i = start_Tdb + t * (end_Tdb - start_Tdb)
        points.append(PathPoint(
            Tdb=round(Tdb_i, 4),
            W=round(W, 7),
            W_display=_w_display(W, unit_system),
        ))
    return points


# ---------------------------------------------------------------------------
# Direct Evaporative Cooling — constant Twb (same physics as adiabatic humid.)
# ---------------------------------------------------------------------------

class DirectEvaporativeSolver(ProcessSolver):
    """Solver for direct evaporative cooling (constant wet-bulb line)."""

    def solve(self, process_input: ProcessInput) -> ProcessOutput:
        pi = process_input

        if pi.effectiveness is None:
            raise ValueError(
                "effectiveness is required for direct evaporative cooling"
            )

        eff = pi.effectiveness
        if eff < 0 or eff > 1:
            raise ValueError(
                f"effectiveness must be between 0 and 1, got {eff}"
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
        Twb = start.Twb

        # End Tdb via effectiveness
        end_Tdb = start.Tdb - eff * (start.Tdb - Twb)

        # End W along constant Twb
        end_W = psychrolib.GetHumRatioFromTWetBulb(end_Tdb, Twb, pi.pressure)
        end = resolve_state_point(
            input_pair=("Tdb", "W"),
            values=(end_Tdb, end_W),
            pressure=pi.pressure,
            unit_system=pi.unit_system,
            label="end",
        )

        # Path along constant Twb curve
        path_points = _generate_constant_twb_path(
            start.Tdb, end_Tdb, Twb, pi.pressure, pi.unit_system,
        )

        metadata = {
            "effectiveness": round(eff, 4),
            "Twb": round(Twb, 4),
            "delta_Tdb": round(end.Tdb - start.Tdb, 4),
            "delta_W": round(end.W - start.W, 7),
            "delta_W_display": _w_display(end.W - start.W, pi.unit_system),
            "start_RH": round(start.RH, 2),
            "end_RH": round(end.RH, 2),
        }

        return ProcessOutput(
            process_type=ProcessType.DIRECT_EVAPORATIVE,
            unit_system=pi.unit_system,
            pressure=pi.pressure,
            start_point=start.model_dump(),
            end_point=end.model_dump(),
            path_points=path_points,
            metadata=metadata,
            warnings=warnings,
        )


# ---------------------------------------------------------------------------
# Indirect Evaporative Cooling — sensible cooling (horizontal path)
# ---------------------------------------------------------------------------

class IndirectEvaporativeSolver(ProcessSolver):
    """Solver for indirect evaporative cooling (sensible cooling only).

    Primary air is cooled at constant humidity ratio through a heat exchanger.
    The limit is the secondary air's wet-bulb temperature.
    """

    def solve(self, process_input: ProcessInput) -> ProcessOutput:
        pi = process_input

        if pi.effectiveness is None:
            raise ValueError(
                "effectiveness is required for indirect evaporative cooling"
            )

        eff = pi.effectiveness
        if eff < 0 or eff > 1:
            raise ValueError(
                f"effectiveness must be between 0 and 1, got {eff}"
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

        # Determine secondary air wet-bulb
        if pi.secondary_air_pair is not None and pi.secondary_air_values is not None:
            secondary = resolve_state_point(
                input_pair=pi.secondary_air_pair,
                values=pi.secondary_air_values,
                pressure=pi.pressure,
                unit_system=pi.unit_system,
                label="secondary",
            )
            Twb_sec = secondary.Twb
        else:
            Twb_sec = start.Twb

        # Sensible cooling: Tdb drops, W stays constant
        end_Tdb = start.Tdb - eff * (start.Tdb - Twb_sec)

        # Validate: Tdb should drop (or stay same at eff=0)
        if end_Tdb > start.Tdb + 0.01:
            warnings.append(
                f"End Tdb ({end_Tdb:.1f}) is above start Tdb ({start.Tdb:.1f}). "
                f"Secondary Twb may be above primary Tdb."
            )

        end = resolve_state_point(
            input_pair=("Tdb", "W"),
            values=(end_Tdb, start.W),
            pressure=pi.pressure,
            unit_system=pi.unit_system,
            label="end",
        )

        # Check if we've crossed the dew point (sensible cooling below Tdp)
        if end_Tdb < start.Tdp:
            warnings.append(
                f"End Tdb ({end_Tdb:.1f}) is below the dew point ({start.Tdp:.1f}). "
                f"In practice, condensation would occur on the heat exchanger."
            )

        # Path: horizontal line
        path_points = _generate_horizontal_path(
            start.Tdb, end_Tdb, start.W, pi.unit_system,
        )

        metadata = {
            "effectiveness": round(eff, 4),
            "secondary_Twb": round(Twb_sec, 4),
            "delta_Tdb": round(end.Tdb - start.Tdb, 4),
            "start_RH": round(start.RH, 2),
            "end_RH": round(end.RH, 2),
        }

        return ProcessOutput(
            process_type=ProcessType.INDIRECT_EVAPORATIVE,
            unit_system=pi.unit_system,
            pressure=pi.pressure,
            start_point=start.model_dump(),
            end_point=end.model_dump(),
            path_points=path_points,
            metadata=metadata,
            warnings=warnings,
        )


# ---------------------------------------------------------------------------
# Indirect-Direct Two-Stage — horizontal then diagonal
# ---------------------------------------------------------------------------

class IndirectDirectEvaporativeSolver(ProcessSolver):
    """Solver for indirect-direct two-stage evaporative cooling.

    Stage 1 (IEC): Sensible cooling at constant W toward secondary Twb.
    Stage 2 (DEC): Adiabatic cooling along constant Twb of the intermediate state.
    """

    def solve(self, process_input: ProcessInput) -> ProcessOutput:
        pi = process_input

        if pi.iec_effectiveness is None:
            raise ValueError(
                "iec_effectiveness is required for indirect-direct evaporative cooling"
            )
        if pi.dec_effectiveness is None:
            raise ValueError(
                "dec_effectiveness is required for indirect-direct evaporative cooling"
            )

        iec_eff = pi.iec_effectiveness
        dec_eff = pi.dec_effectiveness

        if iec_eff < 0 or iec_eff > 1:
            raise ValueError(
                f"iec_effectiveness must be between 0 and 1, got {iec_eff}"
            )
        if dec_eff < 0 or dec_eff > 1:
            raise ValueError(
                f"dec_effectiveness must be between 0 and 1, got {dec_eff}"
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

        # Secondary air wet-bulb (for IEC stage)
        if pi.secondary_air_pair is not None and pi.secondary_air_values is not None:
            secondary = resolve_state_point(
                input_pair=pi.secondary_air_pair,
                values=pi.secondary_air_values,
                pressure=pi.pressure,
                unit_system=pi.unit_system,
                label="secondary",
            )
            Twb_sec = secondary.Twb
        else:
            Twb_sec = start.Twb

        # --- Stage 1: IEC (horizontal, sensible cooling) ---
        mid_Tdb = start.Tdb - iec_eff * (start.Tdb - Twb_sec)
        mid = resolve_state_point(
            input_pair=("Tdb", "W"),
            values=(mid_Tdb, start.W),
            pressure=pi.pressure,
            unit_system=pi.unit_system,
            label="intermediate",
        )

        # --- Stage 2: DEC (along constant Twb of intermediate state) ---
        Twb_mid = mid.Twb
        end_Tdb = mid.Tdb - dec_eff * (mid.Tdb - Twb_mid)
        end_W = psychrolib.GetHumRatioFromTWetBulb(end_Tdb, Twb_mid, pi.pressure)

        end = resolve_state_point(
            input_pair=("Tdb", "W"),
            values=(end_Tdb, end_W),
            pressure=pi.pressure,
            unit_system=pi.unit_system,
            label="end",
        )

        # Path: horizontal segment then curved segment
        path_iec = _generate_horizontal_path(
            start.Tdb, mid_Tdb, start.W, pi.unit_system, n_points=6,
        )
        path_dec = _generate_constant_twb_path(
            mid.Tdb, end_Tdb, Twb_mid, pi.pressure, pi.unit_system, n_points=14,
        )
        # Combine, removing duplicate at junction
        path_points = path_iec + path_dec[1:]

        metadata = {
            "iec_effectiveness": round(iec_eff, 4),
            "dec_effectiveness": round(dec_eff, 4),
            "secondary_Twb": round(Twb_sec, 4),
            "intermediate_Tdb": round(mid.Tdb, 4),
            "intermediate_RH": round(mid.RH, 2),
            "intermediate_Twb": round(Twb_mid, 4),
            "delta_Tdb_total": round(end.Tdb - start.Tdb, 4),
            "delta_W": round(end.W - start.W, 7),
            "delta_W_display": _w_display(end.W - start.W, pi.unit_system),
            "start_RH": round(start.RH, 2),
            "end_RH": round(end.RH, 2),
        }

        return ProcessOutput(
            process_type=ProcessType.INDIRECT_DIRECT_EVAPORATIVE,
            unit_system=pi.unit_system,
            pressure=pi.pressure,
            start_point=start.model_dump(),
            end_point=end.model_dump(),
            path_points=path_points,
            metadata=metadata,
            warnings=warnings,
        )
