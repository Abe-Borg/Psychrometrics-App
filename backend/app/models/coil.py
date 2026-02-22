"""
Pydantic models for coil analysis input/output.
"""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

from app.config import UnitSystem, DEFAULT_PRESSURE_IP
from app.models.process import PathPoint


class CoilMode(str, Enum):
    FORWARD = "forward"   # entering + ADP + BF → leaving + loads
    REVERSE = "reverse"   # entering + leaving → ADP + BF + loads


class CoilInput(BaseModel):
    """Input for coil analysis calculation."""

    mode: CoilMode
    unit_system: UnitSystem = UnitSystem.IP
    pressure: float = DEFAULT_PRESSURE_IP

    # Entering air (required for both modes)
    entering_pair: tuple[str, str]
    entering_values: tuple[float, float]

    # Forward mode fields
    adp_Tdb: Optional[float] = None
    bypass_factor: Optional[float] = None

    # Reverse mode fields
    leaving_pair: Optional[tuple[str, str]] = None
    leaving_values: Optional[tuple[float, float]] = None

    # Optional: airflow for absolute load calculation (otherwise per-unit-mass)
    airflow: Optional[float] = None  # CFM (IP) or m³/s (SI)

    # Optional: water side for GPM estimate
    water_entering_temp: Optional[float] = None  # °F or °C
    water_leaving_temp: Optional[float] = None   # °F or °C


class CoilOutput(BaseModel):
    """Result of a coil analysis calculation."""

    unit_system: UnitSystem
    pressure: float
    mode: CoilMode

    entering: dict       # full StatePointOutput as dict
    leaving: dict        # full StatePointOutput as dict
    adp: dict            # full StatePointOutput as dict (saturated)

    bypass_factor: float
    contact_factor: float

    # Load breakdown
    Qs: float            # sensible heat
    Ql: float            # latent heat
    Qt: float            # total heat
    SHR: float           # sensible heat ratio
    load_unit: str       # "BTU/lb" or "BTU/hr" (IP); "kJ/kg" or "W" (SI)

    # Optional GPM/flow rate
    gpm: Optional[float] = None  # GPM (IP) or L/s (SI)

    # Path for chart overlay
    path_points: list[PathPoint]

    warnings: list[str] = Field(default_factory=list)
