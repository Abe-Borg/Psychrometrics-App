"""
Pydantic models for ASHRAE design day conditions overlay.
"""

from pydantic import BaseModel, Field
from typing import Optional
from app.config import UnitSystem


class DesignDayCondition(BaseModel):
    """A single design condition (e.g., 0.4% cooling DB with coincident WB)."""
    label: str
    Tdb: float
    Twb: Optional[float] = None
    category: str  # "cooling_db", "cooling_wb", "heating"


class DesignDayLocation(BaseModel):
    """A location with its design day data."""
    name: str
    state: str
    country: str
    elevation_ft: float
    climate_zone: str
    conditions: list[DesignDayCondition]


class DesignDaySearchResult(BaseModel):
    """Abbreviated location info for search results."""
    name: str
    state: str
    country: str
    climate_zone: str
    elevation_ft: float


class DesignDayResolveInput(BaseModel):
    """Input for resolving design day conditions to full state points."""
    location_name: str
    location_state: str = ""
    condition_labels: list[str] = Field(
        default_factory=list,
        description="Which conditions to resolve. Empty = all."
    )
    unit_system: UnitSystem = "IP"
    pressure: Optional[float] = None  # Override; default computed from elevation


class DesignDayResolvedPoint(BaseModel):
    """A fully resolved state point with design day metadata."""
    condition_label: str
    category: str
    Tdb: float
    Twb: float
    Tdp: float
    RH: float
    W: float
    W_display: float
    h: float
    v: float
    unit_system: str


class DesignDayResolveOutput(BaseModel):
    """Result of resolving design day conditions."""
    location: DesignDaySearchResult
    points: list[DesignDayResolvedPoint]
    pressure_used: float
    unit_system: str
