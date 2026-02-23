"""
Orchestrator for weather data analysis pipeline.

Parses EPW → computes psychrometric states → extracts extreme design points →
clusters → packages everything into a structured result.
"""

import numpy as np

from app.config import UnitSystem
from app.engine.tmy_processor import parse_epw_raw
from app.engine.weather_analysis.psychrometric_calc import compute_hourly_states
from app.engine.weather_analysis.clustering import cluster_weather_data
from app.models.weather_analysis import (
    EPWLocation,
    HourlyPsychroState,
    DesignPoint,
    ClusterSummary,
    WeatherChartPoint,
    WeatherAnalysisOutput,
)


def extract_design_conditions(
    epw_content: str,
    n_clusters: int = 5,
    unit_system: str = "IP",
) -> WeatherAnalysisOutput:
    """
    Run the full weather analysis pipeline on EPW file content.

    Args:
        epw_content: Raw EPW file text.
        n_clusters: Number of clusters for k-means (default 5).
        unit_system: "IP" or "SI" for output display units.

    Returns:
        WeatherAnalysisOutput with design points, cluster summaries, and chart data.
    """
    # Step 1: Parse EPW file
    raw = parse_epw_raw(epw_content)
    location_dict = raw["location"]
    location = EPWLocation(**location_dict)

    # Step 2: Compute full psychrometric states (SI)
    states = compute_hourly_states(raw["records"])
    if len(states) == 0:
        raise ValueError("No valid psychrometric states could be computed.")

    # Step 3: Extract extreme design points
    peak_cooling = _extract_peak_cooling(states)
    peak_heating = _extract_peak_heating(states)
    peak_dehum = _extract_peak_dehumidification(states, peak_cooling)

    # Step 4: Cluster and extract intermediate points
    cluster_result = cluster_weather_data(states, n_clusters=n_clusters)
    labels = cluster_result["labels"]
    cluster_infos = cluster_result["cluster_infos"]

    # Step 5: Build design points list
    design_points: list[DesignPoint] = []

    design_points.append(_state_to_design_point(
        peak_cooling, "Peak Cooling", "extreme", unit_system,
    ))
    design_points.append(_state_to_design_point(
        peak_heating, "Peak Heating", "extreme", unit_system,
    ))
    design_points.append(_state_to_design_point(
        peak_dehum, "Peak Dehumidification", "extreme", unit_system,
    ))

    for ci in cluster_infos:
        dp = _state_to_design_point(
            ci["worst_case_state"],
            f"{ci['label']} (Worst Case)",
            "cluster_worst_case",
            unit_system,
            cluster_id=ci["cluster_id"],
            hours_in_cluster=ci["hour_count"],
        )
        design_points.append(dp)

    # Step 6: Build cluster summaries
    cluster_summary: list[ClusterSummary] = []
    for ci in cluster_infos:
        cluster_summary.append(ClusterSummary(
            cluster_id=ci["cluster_id"],
            label=ci["label"],
            hour_count=ci["hour_count"],
            fraction_of_year=ci["fraction_of_year"],
            centroid_dry_bulb=_convert_temp(ci["centroid_tdb_c"], unit_system),
            centroid_humidity_ratio=_convert_w(ci["centroid_w"], unit_system),
        ))

    # Step 7: Build chart data (all hours with cluster assignment)
    chart_data: list[WeatherChartPoint] = []
    for i, state in enumerate(states):
        chart_data.append(WeatherChartPoint(
            dry_bulb=round(_convert_temp(state.dry_bulb_c, unit_system), 2),
            humidity_ratio=round(_convert_w(state.humidity_ratio, unit_system), 2),
            cluster_id=labels[i],
        ))

    return WeatherAnalysisOutput(
        unit_system=unit_system,
        location=location,
        design_points=design_points,
        cluster_summary=cluster_summary,
        chart_data=chart_data,
        total_hours=len(states),
    )


def _extract_peak_cooling(states: list[HourlyPsychroState]) -> HourlyPsychroState:
    """Peak cooling = hour with highest moist air enthalpy."""
    return max(states, key=lambda s: s.enthalpy_j_per_kg)


def _extract_peak_heating(states: list[HourlyPsychroState]) -> HourlyPsychroState:
    """Peak heating = hour with lowest dry-bulb temperature."""
    return min(states, key=lambda s: s.dry_bulb_c)


def _extract_peak_dehumidification(
    states: list[HourlyPsychroState],
    peak_cooling: HourlyPsychroState,
) -> HourlyPsychroState:
    """
    Peak dehumidification = highest humidity ratio at moderate temperature.

    Filters to hours where Tdb < 85% of peak cooling Tdb, then selects
    the hour with the highest humidity ratio. If the filter yields no
    results (e.g., very narrow temperature range), falls back to highest W overall.
    """
    threshold_c = peak_cooling.dry_bulb_c * 0.85
    moderate_hours = [s for s in states if s.dry_bulb_c < threshold_c]

    if not moderate_hours:
        # Fallback: just use the hour with highest W
        moderate_hours = states

    return max(moderate_hours, key=lambda s: s.humidity_ratio)


def _state_to_design_point(
    state: HourlyPsychroState,
    label: str,
    point_type: str,
    unit_system: str,
    cluster_id: int | None = None,
    hours_in_cluster: int | None = None,
) -> DesignPoint:
    """Convert a HourlyPsychroState (SI) to a DesignPoint in display units."""
    return DesignPoint(
        label=label,
        point_type=point_type,
        dry_bulb=round(_convert_temp(state.dry_bulb_c, unit_system), 1),
        wet_bulb=round(_convert_temp(state.wet_bulb_c, unit_system), 1),
        dewpoint=round(_convert_temp(state.dewpoint_c, unit_system), 1),
        humidity_ratio=round(_convert_w(state.humidity_ratio, unit_system), 1),
        enthalpy=round(_convert_enthalpy(state.enthalpy_j_per_kg, unit_system), 1),
        relative_humidity=round(state.relative_humidity, 4),
        specific_volume=round(
            _convert_specific_volume(state.specific_volume, unit_system), 2
        ),
        month=state.month,
        day=state.day,
        hour=state.hour,
        cluster_id=cluster_id,
        hours_in_cluster=hours_in_cluster,
    )


# --- Unit conversion helpers ---

def _convert_temp(temp_c: float, unit_system: str) -> float:
    """Convert temperature from °C to display units."""
    if unit_system == "IP":
        return temp_c * 9.0 / 5.0 + 32.0
    return temp_c


def _convert_w(w_kg_kg: float, unit_system: str) -> float:
    """Convert humidity ratio from kg/kg to display units (grains/lb or g/kg)."""
    if unit_system == "IP":
        return w_kg_kg * 7000.0  # grains per lb
    return w_kg_kg * 1000.0  # g per kg


def _convert_enthalpy(h_j_per_kg: float, unit_system: str) -> float:
    """Convert enthalpy from J/kg to display units (BTU/lb or kJ/kg)."""
    if unit_system == "IP":
        return h_j_per_kg / 2326.0  # J/kg to BTU/lb
    return h_j_per_kg / 1000.0  # J/kg to kJ/kg


def _convert_specific_volume(v_m3_per_kg: float, unit_system: str) -> float:
    """Convert specific volume from m³/kg to display units (ft³/lb or m³/kg)."""
    if unit_system == "IP":
        return v_m3_per_kg * 16.018  # m³/kg to ft³/lb
    return v_m3_per_kg
