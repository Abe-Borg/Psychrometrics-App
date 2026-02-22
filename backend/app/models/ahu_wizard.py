"""
Pydantic models for the AHU (Air Handling Unit) Wizard.

The wizard orchestrates existing process solvers to model a full AHU chain:
  OA (+ RA mixing) → cooling coil → optional reheat → supply air
"""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

from app.config import UnitSystem, DEFAULT_PRESSURE_IP


class AHUType(str, Enum):
    MIXED_AIR = "mixed_air"     # OA + RA mixing box
    FULL_OA = "full_oa"         # 100% outside air (DOAS)
    ECONOMIZER = "economizer"   # Economizer (same as mixed_air for calculation)


class AHUWizardInput(BaseModel):
    """Input for the AHU wizard calculation."""

    ahu_type: AHUType
    unit_system: UnitSystem = UnitSystem.IP
    pressure: float = DEFAULT_PRESSURE_IP

    # Outside air conditions
    oa_Tdb: float = Field(..., description="Outside air dry-bulb temperature")
    oa_coincident: float = Field(
        ..., description="Coincident value: Twb or RH depending on oa_input_type"
    )
    oa_input_type: str = Field(
        default="Twb",
        description="Type of coincident value: 'Twb' or 'RH'",
    )

    # Return air conditions (mixed_air / economizer only)
    ra_Tdb: Optional[float] = Field(
        None, description="Return air dry-bulb temperature"
    )
    ra_RH: Optional[float] = Field(
        None, description="Return air relative humidity (%)"
    )

    # Mixing
    oa_fraction: Optional[float] = Field(
        None, description="Outside air fraction (0-1). 1.0 for full OA."
    )
    oa_cfm: Optional[float] = Field(
        None, description="Outside air volume flow (CFM or m³/s)"
    )
    ra_cfm: Optional[float] = Field(
        None, description="Return air volume flow (CFM or m³/s)"
    )

    # Supply air target
    supply_Tdb: float = Field(..., description="Target supply air dry-bulb temperature")
    supply_RH: Optional[float] = Field(
        None, description="Optional target supply air RH (%)"
    )

    # Optional room loads for airflow sizing
    room_sensible_load: Optional[float] = Field(
        None, description="Room sensible load (BTU/hr or W)"
    )
    room_total_load: Optional[float] = Field(
        None, description="Room total load (BTU/hr or W)"
    )
    total_airflow: Optional[float] = Field(
        None, description="Total supply airflow if known (CFM or m³/s)"
    )


class AHUWizardOutput(BaseModel):
    """Result of the AHU wizard calculation."""

    ahu_type: AHUType
    unit_system: UnitSystem

    # All resolved state points (as dicts matching StatePointOutput)
    oa_point: dict
    ra_point: Optional[dict] = None
    mixed_point: Optional[dict] = None
    coil_leaving: dict
    supply_point: dict  # After reheat if needed; same as coil_leaving if no reheat

    # Process chain serialized for chart overlay
    processes: list[dict] = Field(default_factory=list)

    # Loads summary (per-unit-mass basis)
    cooling_Qs: float = Field(..., description="Sensible cooling load (per lb/kg)")
    cooling_Ql: float = Field(..., description="Latent cooling load (per lb/kg)")
    cooling_Qt: float = Field(..., description="Total cooling load (per lb/kg)")
    reheat_Q: Optional[float] = Field(
        None, description="Reheat load (per lb/kg), if reheat is required"
    )
    shr: float = Field(..., description="Sensible heat ratio of cooling process")

    # Airflow
    supply_cfm: Optional[float] = Field(
        None, description="Computed supply airflow (CFM or m³/s)"
    )

    # Coil info
    adp_Tdb: Optional[float] = None
    bypass_factor: Optional[float] = None

    # Metadata
    pressure: float
    oa_fraction_used: float
    needs_reheat: bool
    warnings: list[str] = Field(default_factory=list)
