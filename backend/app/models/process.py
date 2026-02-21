"""
Pydantic models for psychrometric process input/output.
"""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

from app.config import UnitSystem, DEFAULT_PRESSURE_IP


class ProcessType(str, Enum):
    SENSIBLE_HEATING = "sensible_heating"
    SENSIBLE_COOLING = "sensible_cooling"
    COOLING_DEHUMIDIFICATION = "cooling_dehumidification"
    ADIABATIC_MIXING = "adiabatic_mixing"


class SensibleMode(str, Enum):
    TARGET_TDB = "target_tdb"
    DELTA_T = "delta_t"
    HEAT_AND_AIRFLOW = "heat_and_airflow"


class CoolingDehumMode(str, Enum):
    FORWARD = "forward"  # ADP + BF → leaving state
    REVERSE = "reverse"  # entering + leaving → ADP + BF


class ProcessInput(BaseModel):
    """Input for a psychrometric process calculation."""

    process_type: ProcessType
    unit_system: UnitSystem = UnitSystem.IP
    pressure: float = DEFAULT_PRESSURE_IP

    # Start state: resolved from an input pair (reuses existing resolver)
    start_point_pair: tuple[str, str]
    start_point_values: tuple[float, float]

    # Sensible heating/cooling parameters
    sensible_mode: Optional[SensibleMode] = None
    target_Tdb: Optional[float] = None
    delta_T: Optional[float] = None
    Q_sensible: Optional[float] = None  # BTU/hr (IP) or W (SI)
    airflow_cfm: Optional[float] = None  # CFM (IP) or m³/s (SI)

    # Cooling & dehumidification parameters
    cooling_dehum_mode: Optional[CoolingDehumMode] = None
    adp_Tdb: Optional[float] = None
    bypass_factor: Optional[float] = None  # 0 < BF < 1
    leaving_Tdb: Optional[float] = None
    leaving_RH: Optional[float] = None

    # Adiabatic mixing parameters
    stream2_point_pair: Optional[tuple[str, str]] = None
    stream2_point_values: Optional[tuple[float, float]] = None
    mixing_fraction: Optional[float] = None  # stream 1 fraction: m1/(m1+m2)


class PathPoint(BaseModel):
    """A point along a process path for chart rendering."""

    Tdb: float
    W: float
    W_display: float


class ProcessOutput(BaseModel):
    """Result of a process calculation."""

    process_type: ProcessType
    unit_system: UnitSystem
    pressure: float

    start_point: dict  # Full StatePointOutput as dict
    end_point: dict  # Full StatePointOutput as dict
    path_points: list[PathPoint]

    metadata: dict = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
