"""
Pydantic models for SHR (Sensible Heat Ratio) line calculations.
"""

from typing import Optional

from pydantic import BaseModel, Field

from app.config import UnitSystem, DEFAULT_PRESSURE_IP
from app.models.process import PathPoint


class SHRLineInput(BaseModel):
    """Input for SHR line calculation."""

    unit_system: UnitSystem = UnitSystem.IP
    pressure: float = DEFAULT_PRESSURE_IP

    # Room state point
    room_pair: tuple[str, str]
    room_values: tuple[float, float]

    # SHR value (0 < SHR ≤ 1)
    shr: float


class SHRLineOutput(BaseModel):
    """Result of an SHR line calculation."""

    room_point: dict         # full StatePointOutput as dict
    shr: float
    slope_dW_dTdb: float     # slope in W (lb/lb or kg/kg) per degree
    line_points: list[PathPoint]  # points for chart rendering
    adp: dict                # ADP state (intersection with saturation curve)
    adp_Tdb: float

    warnings: list[str] = Field(default_factory=list)


class GSHRInput(BaseModel):
    """Input for Grand SHR (GSHR) and Effective SHR (ESHR) calculation."""

    unit_system: UnitSystem = UnitSystem.IP
    pressure: float = DEFAULT_PRESSURE_IP

    # Room conditions
    room_pair: tuple[str, str]
    room_values: tuple[float, float]

    # Outdoor air conditions
    oa_pair: tuple[str, str]
    oa_values: tuple[float, float]

    # Room loads
    room_sensible_load: float   # BTU/hr or W
    room_total_load: float      # BTU/hr or W

    # Ventilation parameters
    oa_fraction: float          # 0–1 (fraction of total supply airflow that is OA)
    total_airflow: float        # CFM (IP) or m³/s (SI)

    # Optional: bypass factor for ESHR calculation
    bypass_factor: Optional[float] = None


class GSHROutput(BaseModel):
    """Result of a GSHR/ESHR calculation."""

    room_point: dict
    oa_point: dict
    mixed_point: dict         # mixed air state (OA + return air)

    room_shr: float           # room SHR = Qs_room / Qt_room
    gshr: float               # grand SHR
    eshr: Optional[float] = None  # effective SHR (if BF provided)

    # SHR line data for chart
    room_shr_line: list[PathPoint]
    gshr_line: list[PathPoint]
    eshr_line: Optional[list[PathPoint]] = None

    # ADP intersections
    room_shr_adp: dict
    gshr_adp: dict
    eshr_adp: Optional[dict] = None

    warnings: list[str] = Field(default_factory=list)
