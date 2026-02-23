"""
Pydantic models for weather data analysis and design condition extraction.
"""

from pydantic import BaseModel
from typing import Optional

from app.config import UnitSystem


class EPWLocation(BaseModel):
    """Location metadata extracted from EPW file header."""
    city: str
    state: str
    country: str
    latitude: float
    longitude: float
    timezone: float
    elevation: float  # meters


class HourlyPsychroState(BaseModel):
    """Full psychrometric state for a single hour, stored in SI internally."""
    month: int
    day: int
    hour: int
    dry_bulb_c: float
    wet_bulb_c: float
    dewpoint_c: float
    humidity_ratio: float       # kg/kg
    relative_humidity: float    # fraction 0.0-1.0
    enthalpy_j_per_kg: float   # J/kg
    specific_volume: float     # m³/kg
    pressure_pa: float


class DesignPoint(BaseModel):
    """A single design condition point (extreme or cluster worst-case)."""
    label: str
    point_type: str  # "extreme" or "cluster_worst_case"
    dry_bulb: float
    wet_bulb: float
    dewpoint: float
    humidity_ratio: float  # display units (grains/lb or g/kg)
    enthalpy: float        # display units (BTU/lb or kJ/kg)
    relative_humidity: float  # fraction 0.0-1.0
    specific_volume: float   # display units (ft³/lb or m³/kg)
    month: int
    day: int
    hour: int
    cluster_id: Optional[int] = None
    hours_in_cluster: Optional[int] = None


class ClusterSummary(BaseModel):
    """Summary info for a single cluster."""
    cluster_id: int
    label: str
    hour_count: int
    fraction_of_year: float
    centroid_dry_bulb: float      # display units
    centroid_humidity_ratio: float  # display units


class WeatherChartPoint(BaseModel):
    """Minimal point for chart plotting (all 8760 hours)."""
    dry_bulb: float
    humidity_ratio: float  # display units
    cluster_id: int


class WeatherAnalysisOutput(BaseModel):
    """Full result from weather analysis pipeline."""
    unit_system: UnitSystem
    location: EPWLocation
    design_points: list[DesignPoint]
    cluster_summary: list[ClusterSummary]
    chart_data: list[WeatherChartPoint]
    total_hours: int
