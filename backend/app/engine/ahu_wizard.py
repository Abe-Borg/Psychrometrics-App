"""
AHU Wizard engine — orchestrates existing solvers to model a full AHU chain.

Sequence:
  1. Resolve OA state point
  2. Resolve RA state point (if mixed-air or economizer)
  3. Compute mixed-air state (if mixed-air or economizer)
  4. Determine coil entering condition (mixed or OA)
  5. Calculate cooling & dehumidification from entering → supply target
  6. Check if reheat is needed (coil leaving Tdb < supply target Tdb)
  7. Calculate reheat if needed
  8. Compute loads, SHR, optional airflow sizing
"""

import psychrolib

from app.config import UnitSystem, GRAINS_PER_LB
from app.engine.state_resolver import resolve_state_point
from app.engine.processes.utils import (
    set_unit_system,
    w_display,
    find_adp,
    generate_path_points,
)
from app.models.ahu_wizard import AHUType, AHUWizardInput, AHUWizardOutput
from app.models.process import PathPoint


def calculate_ahu(inp: AHUWizardInput) -> AHUWizardOutput:
    """Run the full AHU wizard calculation."""
    set_unit_system(inp.unit_system)
    warnings: list[str] = []

    # ── Step 1: Resolve OA state ──
    if inp.oa_input_type == "Twb":
        oa_pair = ("Tdb", "Twb")
    else:
        oa_pair = ("Tdb", "RH")

    oa = resolve_state_point(
        input_pair=oa_pair,
        values=(inp.oa_Tdb, inp.oa_coincident),
        pressure=inp.pressure,
        unit_system=inp.unit_system,
        label="Outside Air",
    )

    # ── Step 2: Resolve RA state (if applicable) ──
    ra = None
    mixed = None
    oa_fraction = 1.0
    processes: list[dict] = []

    if inp.ahu_type in (AHUType.MIXED_AIR, AHUType.ECONOMIZER):
        if inp.ra_Tdb is None or inp.ra_RH is None:
            raise ValueError(
                "ra_Tdb and ra_RH are required for mixed-air or economizer AHU types"
            )

        ra = resolve_state_point(
            input_pair=("Tdb", "RH"),
            values=(inp.ra_Tdb, inp.ra_RH),
            pressure=inp.pressure,
            unit_system=inp.unit_system,
            label="Return Air",
        )

        # Determine OA fraction
        if inp.oa_fraction is not None:
            oa_fraction = inp.oa_fraction
        elif inp.oa_cfm is not None and inp.ra_cfm is not None:
            total = inp.oa_cfm + inp.ra_cfm
            if total <= 0:
                raise ValueError("Sum of oa_cfm and ra_cfm must be positive")
            oa_fraction = inp.oa_cfm / total
        else:
            raise ValueError(
                "Either oa_fraction or both oa_cfm and ra_cfm must be provided "
                "for mixed-air AHU types"
            )

        if oa_fraction < 0.0 or oa_fraction > 1.0:
            raise ValueError(f"OA fraction must be 0-1, got {oa_fraction}")

        # ── Step 3: Compute mixed-air state ──
        W_mix = oa_fraction * oa.W + (1.0 - oa_fraction) * ra.W
        h_mix = oa_fraction * oa.h + (1.0 - oa_fraction) * ra.h
        Tdb_mix = psychrolib.GetTDryBulbFromEnthalpyAndHumRatio(h_mix, W_mix)

        mixed = resolve_state_point(
            input_pair=("Tdb", "W"),
            values=(Tdb_mix, W_mix),
            pressure=inp.pressure,
            unit_system=inp.unit_system,
            label="Mixed Air",
        )

        # Create mixing process for chart
        mix_path = generate_path_points(
            oa.Tdb, oa.W, ra.Tdb, ra.W, inp.unit_system
        )
        processes.append({
            "process_type": "adiabatic_mixing",
            "unit_system": inp.unit_system.value,
            "pressure": inp.pressure,
            "start_point": oa.model_dump(),
            "end_point": mixed.model_dump(),
            "path_points": [p.model_dump() for p in mix_path],
            "metadata": {
                "stream2": ra.model_dump(),
                "mixing_fraction": round(oa_fraction, 4),
            },
            "warnings": [],
        })

        coil_entering = mixed
    else:
        # Full OA — coil entering = OA directly
        oa_fraction = 1.0
        coil_entering = oa

    # ── Step 4-5: Determine cooling requirements ──
    # The coil must bring the entering air to the supply target.
    # If the supply target Tdb is below the entering Tdb, cooling is needed.
    # If W needs to decrease, dehumidification occurs (cooling below dew point).

    supply_Tdb_target = inp.supply_Tdb

    # Determine if we need dehumidification or just sensible cooling
    entering_Tdb = coil_entering.Tdb
    entering_W = coil_entering.W

    if entering_Tdb <= supply_Tdb_target:
        # No cooling needed — entering air is already at or below supply target
        warnings.append(
            f"Entering air Tdb ({entering_Tdb:.1f}) is already at or below "
            f"supply target ({supply_Tdb_target:.1f}). No cooling needed."
        )
        coil_leaving = coil_entering
        cooling_process = None
        adp_Tdb = None
        bypass_factor = None
        needs_reheat = False
    else:
        # Need cooling. Determine target supply RH or use coil leaving at supply Tdb.
        # If supply_RH is specified, resolve the supply target state.
        # Otherwise, assume we cool along the coil process line to supply_Tdb.

        if inp.supply_RH is not None:
            # Explicit supply RH target — resolve the supply state
            supply_target_state = resolve_state_point(
                input_pair=("Tdb", "RH"),
                values=(supply_Tdb_target, inp.supply_RH),
                pressure=inp.pressure,
                unit_system=inp.unit_system,
                label="Supply Target",
            )
            supply_target_W = supply_target_state.W
        else:
            # No RH specified. We need to decide the coil leaving condition.
            # Common approach: if the entering dew point is above the supply Tdb,
            # dehumidification will occur. We'll use the typical coil assumption:
            # leaving at 90-95% RH at the supply Tdb.
            Tdp_entering = coil_entering.Tdp
            if Tdp_entering > supply_Tdb_target:
                # Dehumidification will occur. Assume coil leaves at 90% RH.
                supply_target_state = resolve_state_point(
                    input_pair=("Tdb", "RH"),
                    values=(supply_Tdb_target, 90.0),
                    pressure=inp.pressure,
                    unit_system=inp.unit_system,
                    label="Supply Target",
                )
                supply_target_W = supply_target_state.W
                warnings.append(
                    "No supply RH specified. Assuming 90% RH at coil leaving "
                    "(typical for cooling & dehumidification)."
                )
            else:
                # Sensible cooling only (entering dew point is below supply Tdb)
                supply_target_W = entering_W

        # Check if this is truly sensible-only (W doesn't change)
        is_sensible_only = abs(supply_target_W - entering_W) < 1e-7

        if is_sensible_only:
            # Sensible cooling only — horizontal line on chart
            coil_leaving = resolve_state_point(
                input_pair=("Tdb", "W"),
                values=(supply_Tdb_target, entering_W),
                pressure=inp.pressure,
                unit_system=inp.unit_system,
                label="Coil Leaving",
            )
            adp_Tdb = None
            bypass_factor = None

            # Create sensible cooling process
            path = generate_path_points(
                coil_entering.Tdb, coil_entering.W,
                coil_leaving.Tdb, coil_leaving.W,
                inp.unit_system,
            )
            processes.append({
                "process_type": "sensible_cooling",
                "unit_system": inp.unit_system.value,
                "pressure": inp.pressure,
                "start_point": coil_entering.model_dump(),
                "end_point": coil_leaving.model_dump(),
                "path_points": [p.model_dump() for p in path],
                "metadata": {"delta_T": round(coil_leaving.Tdb - coil_entering.Tdb, 4)},
                "warnings": [],
            })
        else:
            # Cooling with dehumidification — find ADP via reverse method
            coil_leaving = resolve_state_point(
                input_pair=("Tdb", "W"),
                values=(supply_Tdb_target, supply_target_W),
                pressure=inp.pressure,
                unit_system=inp.unit_system,
                label="Coil Leaving",
            )

            try:
                adp_Tdb_val = find_adp(
                    entering_Tdb, entering_W,
                    coil_leaving.Tdb, coil_leaving.W,
                    inp.pressure, inp.unit_system,
                )
                adp_Tdb = round(adp_Tdb_val, 4)

                # Compute bypass factor
                if abs(entering_Tdb - adp_Tdb_val) > 1e-10:
                    bf = (coil_leaving.Tdb - adp_Tdb_val) / (entering_Tdb - adp_Tdb_val)
                    bypass_factor = round(max(0.0, min(1.0, bf)), 4)
                else:
                    bypass_factor = None
            except (ValueError, Exception):
                adp_Tdb = None
                bypass_factor = None
                warnings.append(
                    "Could not determine ADP/BF for the cooling process. "
                    "Results are still valid but coil geometry analysis is unavailable."
                )

            # Create cooling & dehumidification process
            path = generate_path_points(
                coil_entering.Tdb, coil_entering.W,
                coil_leaving.Tdb, coil_leaving.W,
                inp.unit_system,
            )

            metadata: dict = {
                "Qs": round(_sensible_load(coil_entering, coil_leaving, inp.unit_system), 4),
                "Ql": round(_latent_load(coil_entering, coil_leaving, inp.unit_system), 4),
                "Qt": round(coil_entering.h - coil_leaving.h, 4),
            }
            if adp_Tdb is not None:
                metadata["ADP_Tdb"] = adp_Tdb
            if bypass_factor is not None:
                metadata["BF"] = bypass_factor

            processes.append({
                "process_type": "cooling_dehumidification",
                "unit_system": inp.unit_system.value,
                "pressure": inp.pressure,
                "start_point": coil_entering.model_dump(),
                "end_point": coil_leaving.model_dump(),
                "path_points": [p.model_dump() for p in path],
                "metadata": metadata,
                "warnings": [],
            })

        needs_reheat = False  # Will check below

    # ── Step 6: Check if reheat is needed ──
    # Reheat is needed if the coil leaves at a Tdb below the supply target.
    # This happens when a dehumidification coil overshoots on temperature
    # to achieve the required moisture removal.
    needs_reheat = coil_leaving.Tdb < (supply_Tdb_target - 0.1)
    supply_point = coil_leaving  # default
    reheat_Q = None

    if needs_reheat:
        # Sensible reheat: constant W from coil leaving Tdb up to supply target Tdb
        supply_point = resolve_state_point(
            input_pair=("Tdb", "W"),
            values=(supply_Tdb_target, coil_leaving.W),
            pressure=inp.pressure,
            unit_system=inp.unit_system,
            label="Supply Air",
        )
        reheat_Q = round(supply_point.h - coil_leaving.h, 4)

        # Create reheat process
        path = generate_path_points(
            coil_leaving.Tdb, coil_leaving.W,
            supply_point.Tdb, supply_point.W,
            inp.unit_system,
        )
        processes.append({
            "process_type": "sensible_reheat",
            "unit_system": inp.unit_system.value,
            "pressure": inp.pressure,
            "start_point": coil_leaving.model_dump(),
            "end_point": supply_point.model_dump(),
            "path_points": [p.model_dump() for p in path],
            "metadata": {"delta_T": round(supply_point.Tdb - coil_leaving.Tdb, 4)},
            "warnings": [],
        })

    # ── Step 7: Compute loads and SHR ──
    Qs = _sensible_load(coil_entering, coil_leaving, inp.unit_system)
    Qt = coil_entering.h - coil_leaving.h
    Ql = Qt - Qs
    shr = Qs / Qt if abs(Qt) > 1e-10 else 1.0

    # ── Step 8: Optional airflow sizing ──
    supply_cfm = None
    if inp.room_sensible_load is not None and inp.total_airflow is not None:
        supply_cfm = inp.total_airflow
    elif inp.room_sensible_load is not None:
        # Size airflow from room sensible load
        # Q_s = C × CFM × ΔT, where ΔT = room Tdb - supply Tdb
        # Assume room Tdb = RA Tdb if available, else a default
        room_Tdb = inp.ra_Tdb if inp.ra_Tdb is not None else (
            75.0 if inp.unit_system == UnitSystem.IP else 24.0
        )
        delta_T_room = room_Tdb - supply_point.Tdb
        if abs(delta_T_room) > 0.1:
            v = psychrolib.GetMoistAirVolume(
                supply_point.Tdb, supply_point.W, inp.pressure
            )
            rho = 1.0 / v
            if inp.unit_system == UnitSystem.IP:
                cp = 0.244
                C_factor = 60.0 * rho * cp
                supply_cfm = round(inp.room_sensible_load / (C_factor * delta_T_room), 1)
            else:
                cp = 1006.0
                supply_cfm = round(
                    inp.room_sensible_load / (rho * cp * delta_T_room), 4
                )

    return AHUWizardOutput(
        ahu_type=inp.ahu_type,
        unit_system=inp.unit_system,
        oa_point=oa.model_dump(),
        ra_point=ra.model_dump() if ra else None,
        mixed_point=mixed.model_dump() if mixed else None,
        coil_leaving=coil_leaving.model_dump(),
        supply_point=supply_point.model_dump(),
        processes=processes,
        cooling_Qs=round(Qs, 4),
        cooling_Ql=round(Ql, 4),
        cooling_Qt=round(Qt, 4),
        reheat_Q=reheat_Q,
        shr=round(shr, 4),
        supply_cfm=supply_cfm,
        adp_Tdb=adp_Tdb if 'adp_Tdb' in dir() else None,
        bypass_factor=bypass_factor if 'bypass_factor' in dir() else None,
        pressure=inp.pressure,
        oa_fraction_used=round(oa_fraction, 4),
        needs_reheat=needs_reheat,
        warnings=warnings,
    )


def _sensible_load(
    entering, leaving, unit_system: UnitSystem
) -> float:
    """Compute sensible load per unit mass of dry air."""
    if unit_system == UnitSystem.IP:
        cp = 0.244  # BTU/(lb·°F)
    else:
        cp = 1.006  # kJ/(kg·K)
    return cp * (entering.Tdb - leaving.Tdb)


def _latent_load(
    entering, leaving, unit_system: UnitSystem
) -> float:
    """Compute latent load per unit mass of dry air."""
    Qt = entering.h - leaving.h
    Qs = _sensible_load(entering, leaving, unit_system)
    return Qt - Qs
