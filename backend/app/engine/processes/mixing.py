"""
Adiabatic mixing process solver.

Models the mixing of two airstreams in a mixing box with no external heat
transfer. The mixed state lies on a straight line between the two entering
states on the psychrometric chart, positioned by the mass flow ratio (lever rule).

Conservation equations (dry-air mass basis):
    W_mix = f * W_1 + (1 - f) * W_2
    h_mix = f * h_1 + (1 - f) * h_2

where f = m_1 / (m_1 + m_2) is the stream-1 mass fraction (mixing_fraction).
"""

import psychrolib

from app.config import UnitSystem, GRAINS_PER_LB
from app.engine.state_resolver import resolve_state_point
from app.engine.processes.base import ProcessSolver
from app.models.process import ProcessInput, ProcessOutput, ProcessType, PathPoint


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


def _generate_path_points(
    Tdb_1: float, W_1: float,
    Tdb_2: float, W_2: float,
    unit_system: UnitSystem,
    n_points: int = 12,
) -> list[PathPoint]:
    """Generate points along the straight line from stream 1 to stream 2."""
    points = []
    for i in range(n_points + 1):
        t = i / n_points
        Tdb = Tdb_1 + t * (Tdb_2 - Tdb_1)
        W = W_1 + t * (W_2 - W_1)
        points.append(PathPoint(
            Tdb=round(Tdb, 4),
            W=round(W, 7),
            W_display=_w_display(W, unit_system),
        ))
    return points


class MixingSolver(ProcessSolver):
    """Solver for adiabatic mixing of two airstreams."""

    def solve(self, process_input: ProcessInput) -> ProcessOutput:
        pi = process_input

        # --- Validate required fields ---
        if pi.stream2_point_pair is None or pi.stream2_point_values is None:
            raise ValueError(
                "stream2_point_pair and stream2_point_values are required "
                "for adiabatic mixing"
            )
        if pi.mixing_fraction is None:
            raise ValueError(
                "mixing_fraction is required for adiabatic mixing"
            )

        f = pi.mixing_fraction
        if f < 0.0 or f > 1.0:
            raise ValueError(
                f"mixing_fraction must be between 0 and 1, got {f}"
            )

        warnings: list[str] = []
        if f == 0.0 or f == 1.0:
            stream_label = "stream 1" if f == 1.0 else "stream 2"
            warnings.append(
                f"mixing_fraction is {f} — the mixed state equals {stream_label} "
                f"(no actual mixing occurs)."
            )

        _set_unit_system(pi.unit_system)

        # --- Resolve both entering states ---
        stream1 = resolve_state_point(
            input_pair=pi.start_point_pair,
            values=pi.start_point_values,
            pressure=pi.pressure,
            unit_system=pi.unit_system,
            label="stream_1",
        )

        stream2 = resolve_state_point(
            input_pair=pi.stream2_point_pair,
            values=pi.stream2_point_values,
            pressure=pi.pressure,
            unit_system=pi.unit_system,
            label="stream_2",
        )

        # --- Mass-weighted averages ---
        W_mix = f * stream1.W + (1.0 - f) * stream2.W
        h_mix = f * stream1.h + (1.0 - f) * stream2.h

        # --- Back-calculate Tdb from h and W (algebraic, not iterative) ---
        Tdb_mix = psychrolib.GetTDryBulbFromEnthalpyAndHumRatio(h_mix, W_mix)

        # --- Resolve full mixed state ---
        mixed = resolve_state_point(
            input_pair=("Tdb", "W"),
            values=(Tdb_mix, W_mix),
            pressure=pi.pressure,
            unit_system=pi.unit_system,
            label="mixed",
        )

        # --- Path points: straight line from stream 1 to stream 2 ---
        path_points = _generate_path_points(
            stream1.Tdb, stream1.W,
            stream2.Tdb, stream2.W,
            pi.unit_system,
        )

        metadata = {
            "stream2": stream2.model_dump(),
            "mixing_fraction": round(f, 4),
            "Tdb_mix": round(Tdb_mix, 4),
            "W_mix": round(W_mix, 7),
            "W_mix_display": _w_display(W_mix, pi.unit_system),
            "h_mix": round(h_mix, 4),
        }

        return ProcessOutput(
            process_type=ProcessType.ADIABATIC_MIXING,
            unit_system=pi.unit_system,
            pressure=pi.pressure,
            start_point=stream1.model_dump(),
            end_point=mixed.model_dump(),
            path_points=path_points,
            metadata=metadata,
            warnings=warnings,
        )
