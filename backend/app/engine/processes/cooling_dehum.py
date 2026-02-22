"""
Cooling and dehumidification process solver.

Models the process of cooling air below its dew point through a cooling coil.
The air follows a straight line from the entering condition toward the
apparatus dew point (ADP) on the psychrometric chart. The bypass factor (BF)
determines how far along that line the leaving air ends up.

Two modes:
  - FORWARD: Given entering state + ADP Tdb + BF → compute leaving state
  - REVERSE: Given entering state + leaving state → back-calculate ADP and BF
"""

from app.config import UnitSystem
from app.engine.state_resolver import resolve_state_point
from app.engine.processes.base import ProcessSolver
from app.engine.processes.utils import (
    set_unit_system,
    w_display,
    find_adp,
    generate_path_points,
)
from app.models.process import (
    ProcessInput,
    ProcessOutput,
    ProcessType,
    CoolingDehumMode,
)


class CoolingDehumSolver(ProcessSolver):
    """Solver for cooling and dehumidification processes."""

    def solve(self, process_input: ProcessInput) -> ProcessOutput:
        pi = process_input
        mode = pi.cooling_dehum_mode

        if mode is None:
            raise ValueError(
                "cooling_dehum_mode is required for cooling & dehumidification"
            )

        # Resolve the entering (start) state
        start = resolve_state_point(
            input_pair=pi.start_point_pair,
            values=pi.start_point_values,
            pressure=pi.pressure,
            unit_system=pi.unit_system,
            label="entering",
        )

        warnings: list[str] = []

        if mode == CoolingDehumMode.FORWARD:
            return self._solve_forward(pi, start, warnings)
        elif mode == CoolingDehumMode.REVERSE:
            return self._solve_reverse(pi, start, warnings)
        else:
            raise ValueError(f"Unknown cooling/dehum mode: {mode}")

    def _solve_forward(self, pi, start, warnings):
        """Forward mode: ADP + BF → leaving state."""
        if pi.adp_Tdb is None or pi.bypass_factor is None:
            raise ValueError(
                "adp_Tdb and bypass_factor are required for forward mode"
            )

        BF = pi.bypass_factor
        if not (0.0 < BF < 1.0):
            raise ValueError("bypass_factor must be between 0 and 1 (exclusive)")

        # Resolve ADP as a saturated state (100% RH)
        set_unit_system(pi.unit_system)
        adp = resolve_state_point(
            input_pair=("Tdb", "RH"),
            values=(pi.adp_Tdb, 100.0),
            pressure=pi.pressure,
            unit_system=pi.unit_system,
            label="ADP",
        )

        # Validate: ADP must be below the entering dew point
        if pi.adp_Tdb >= start.Tdp:
            warnings.append(
                f"ADP Tdb ({pi.adp_Tdb:.1f}) is at or above the entering dew point "
                f"({start.Tdp:.1f}). No dehumidification would occur."
            )

        # Leaving conditions via bypass factor
        leaving_Tdb = adp.Tdb + BF * (start.Tdb - adp.Tdb)
        leaving_W = adp.W + BF * (start.W - adp.W)

        # Resolve full leaving state
        end = resolve_state_point(
            input_pair=("Tdb", "W"),
            values=(leaving_Tdb, leaving_W),
            pressure=pi.pressure,
            unit_system=pi.unit_system,
            label="leaving",
        )

        CF = 1.0 - BF

        # Load calculations (per unit mass of dry air)
        Qs = start.h - end.h  # total is not purely sensible, but we use enthalpy components
        # More precise: Qs based on Tdb difference, Ql based on W difference
        if pi.unit_system == UnitSystem.IP:
            cp = 0.244  # BTU/(lb·°F)
        else:
            cp = 1.006  # kJ/(kg·K)

        Qs_precise = cp * (start.Tdb - end.Tdb)
        Qt = start.h - end.h
        Ql = Qt - Qs_precise
        SHR = Qs_precise / Qt if abs(Qt) > 1e-10 else 1.0

        path_points = generate_path_points(
            start.Tdb, start.W, end.Tdb, end.W, pi.unit_system
        )

        metadata = {
            "ADP_Tdb": round(adp.Tdb, 4),
            "ADP_W": round(adp.W, 7),
            "ADP_W_display": w_display(adp.W, pi.unit_system),
            "BF": round(BF, 4),
            "CF": round(CF, 4),
            "Qs": round(Qs_precise, 4),
            "Ql": round(Ql, 4),
            "Qt": round(Qt, 4),
            "SHR": round(SHR, 4),
        }

        return ProcessOutput(
            process_type=ProcessType.COOLING_DEHUMIDIFICATION,
            unit_system=pi.unit_system,
            pressure=pi.pressure,
            start_point=start.model_dump(),
            end_point=end.model_dump(),
            path_points=path_points,
            metadata=metadata,
            warnings=warnings,
        )

    def _solve_reverse(self, pi, start, warnings):
        """Reverse mode: entering + leaving → ADP + BF."""
        if pi.leaving_Tdb is None or pi.leaving_RH is None:
            raise ValueError(
                "leaving_Tdb and leaving_RH are required for reverse mode"
            )

        # Resolve the leaving state
        end = resolve_state_point(
            input_pair=("Tdb", "RH"),
            values=(pi.leaving_Tdb, pi.leaving_RH),
            pressure=pi.pressure,
            unit_system=pi.unit_system,
            label="leaving",
        )

        # Validate: leaving should have lower Tdb and W than entering
        if end.Tdb >= start.Tdb:
            raise ValueError(
                f"Leaving Tdb ({end.Tdb:.1f}) must be less than entering Tdb ({start.Tdb:.1f})"
            )
        if end.W >= start.W:
            warnings.append(
                f"Leaving humidity ratio ({end.W:.6f}) is not less than entering ({start.W:.6f}). "
                f"This looks like sensible cooling only, not cooling & dehumidification."
            )

        # Find the ADP
        set_unit_system(pi.unit_system)
        adp_Tdb = find_adp(
            start.Tdb, start.W, end.Tdb, end.W,
            pi.pressure, pi.unit_system,
        )

        # Resolve full ADP state
        adp = resolve_state_point(
            input_pair=("Tdb", "RH"),
            values=(adp_Tdb, 100.0),
            pressure=pi.pressure,
            unit_system=pi.unit_system,
            label="ADP",
        )

        # Compute BF
        denom = start.Tdb - adp.Tdb
        if abs(denom) < 1e-10:
            raise ValueError("Entering Tdb equals ADP Tdb — cannot compute bypass factor")

        BF = (end.Tdb - adp.Tdb) / denom
        CF = 1.0 - BF

        if BF < 0 or BF > 1:
            raise ValueError(
                f"Computed bypass factor ({BF:.4f}) is out of range (0-1). "
                f"The leaving state may be beyond the ADP."
            )

        # Load calculations
        if pi.unit_system == UnitSystem.IP:
            cp = 0.244
        else:
            cp = 1.006

        Qs_precise = cp * (start.Tdb - end.Tdb)
        Qt = start.h - end.h
        Ql = Qt - Qs_precise
        SHR = Qs_precise / Qt if abs(Qt) > 1e-10 else 1.0

        path_points = generate_path_points(
            start.Tdb, start.W, end.Tdb, end.W, pi.unit_system
        )

        metadata = {
            "ADP_Tdb": round(adp.Tdb, 4),
            "ADP_W": round(adp.W, 7),
            "ADP_W_display": w_display(adp.W, pi.unit_system),
            "BF": round(BF, 4),
            "CF": round(CF, 4),
            "Qs": round(Qs_precise, 4),
            "Ql": round(Ql, 4),
            "Qt": round(Qt, 4),
            "SHR": round(SHR, 4),
        }

        return ProcessOutput(
            process_type=ProcessType.COOLING_DEHUMIDIFICATION,
            unit_system=pi.unit_system,
            pressure=pi.pressure,
            start_point=start.model_dump(),
            end_point=end.model_dump(),
            path_points=path_points,
            metadata=metadata,
            warnings=warnings,
        )
