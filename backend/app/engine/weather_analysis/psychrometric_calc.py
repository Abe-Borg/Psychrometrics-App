"""
Compute full psychrometric state for each hourly weather record.

Takes raw EPW parsed data (tdb_c, tdp_c, pressure_pa per hour) and returns
a list of HourlyPsychroState objects with all derived properties.
"""

import logging

import psychrolib

from app.models.weather_analysis import HourlyPsychroState

logger = logging.getLogger(__name__)


def compute_hourly_states(
    records: list[dict],
) -> list[HourlyPsychroState]:
    """
    Compute full psychrometric state for each hourly record.

    Args:
        records: List of dicts from parse_epw_raw(), each with keys:
            tdb_c, tdp_c, pressure_pa, month, day, hour

    Returns:
        List of HourlyPsychroState with all psychrometric properties (SI units).
        Corrupt records are skipped with a warning.
    """
    psychrolib.SetUnitSystem(psychrolib.SI)

    states: list[HourlyPsychroState] = []

    for idx, rec in enumerate(records):
        try:
            tdb_c = rec["tdb_c"]
            tdp_c = rec["tdp_c"]
            pressure_pa = rec["pressure_pa"]

            # Clamp dewpoint to not exceed dry-bulb (physically impossible)
            if tdp_c > tdb_c:
                tdp_c = tdb_c

            humidity_ratio = psychrolib.GetHumRatioFromTDewPoint(
                tdp_c, pressure_pa
            )
            wet_bulb_c = psychrolib.GetTWetBulbFromTDewPoint(
                tdb_c, tdp_c, pressure_pa
            )
            rh = psychrolib.GetRelHumFromTDewPoint(tdb_c, tdp_c)
            enthalpy = psychrolib.GetMoistAirEnthalpy(tdb_c, humidity_ratio)
            specific_volume = psychrolib.GetMoistAirVolume(
                tdb_c, humidity_ratio, pressure_pa
            )

            states.append(HourlyPsychroState(
                month=rec["month"],
                day=rec["day"],
                hour=rec["hour"],
                dry_bulb_c=tdb_c,
                wet_bulb_c=wet_bulb_c,
                dewpoint_c=tdp_c,
                humidity_ratio=humidity_ratio,
                relative_humidity=rh,
                enthalpy_j_per_kg=enthalpy,
                specific_volume=specific_volume,
                pressure_pa=pressure_pa,
            ))
        except Exception as e:
            logger.warning(
                "Skipping hour %d (month=%s, day=%s, hour=%s): %s",
                idx,
                rec.get("month"),
                rec.get("day"),
                rec.get("hour"),
                e,
            )
            continue

    return states
