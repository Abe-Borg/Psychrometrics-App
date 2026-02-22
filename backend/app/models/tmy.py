"""
Pydantic models for TMY (Typical Meteorological Year) bin data overlay.
"""

from pydantic import BaseModel
from typing import Optional
from app.config import UnitSystem


class TMYScatterPoint(BaseModel):
    """Single hourly data point for scatter plot."""
    Tdb: float
    W_display: float
    hour: int       # 0-8759
    month: int      # 1-12


class TMYProcessOutput(BaseModel):
    """Processed TMY data ready for chart overlay."""
    unit_system: UnitSystem
    scatter_points: list[TMYScatterPoint]
    bin_Tdb_edges: list[float]
    bin_W_edges: list[float]
    bin_matrix: list[list[int]]    # 2D grid [Tdb_bins x W_bins] of hourly counts
    location_name: Optional[str]
    total_hours: int
