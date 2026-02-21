"""
Pydantic models for state point input/output.
"""

from pydantic import BaseModel, Field
from app.config import UnitSystem, DEFAULT_PRESSURE_IP


class StatePointInput(BaseModel):
    """Input model for resolving a state point from two known properties."""

    input_pair: tuple[str, str] = Field(
        ...,
        description="Pair of independent properties, e.g. ('Tdb', 'RH')",
        examples=[("Tdb", "RH"), ("Tdb", "Twb")],
    )
    values: tuple[float, float] = Field(
        ...,
        description="Values for the input pair, in order matching input_pair",
        examples=[(75.0, 50.0), (75.0, 62.5)],
    )
    pressure: float = Field(
        default=DEFAULT_PRESSURE_IP,
        description="Atmospheric pressure. IP: psia, SI: Pa",
    )
    unit_system: UnitSystem = Field(
        default=UnitSystem.IP,
        description="Unit system: IP or SI",
    )
    label: str = Field(
        default="",
        description="Optional user-facing label for this state point",
    )


class StatePointOutput(BaseModel):
    """Full resolved state point with all psychrometric properties."""

    # Input echo
    label: str = ""
    unit_system: UnitSystem = UnitSystem.IP
    pressure: float
    input_pair: tuple[str, str]
    input_values: tuple[float, float]

    # Resolved properties
    Tdb: float = Field(..., description="Dry-bulb temperature")
    Twb: float = Field(..., description="Wet-bulb temperature")
    Tdp: float = Field(..., description="Dew point temperature")
    RH: float = Field(..., description="Relative humidity (0-100%)")
    W: float = Field(..., description="Humidity ratio (lb_w/lb_da or kg_w/kg_da)")
    W_display: float = Field(
        ...,
        description="Humidity ratio for display (grains/lb for IP, g/kg for SI)",
    )
    h: float = Field(..., description="Specific enthalpy (BTU/lb_da or kJ/kg_da)")
    v: float = Field(..., description="Specific volume (ft³/lb_da or m³/kg_da)")
    Pv: float = Field(..., description="Partial vapor pressure")
    Ps: float = Field(..., description="Saturation pressure at Tdb")
    mu: float = Field(..., description="Degree of saturation (0-1)")
