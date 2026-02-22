"""
Pydantic models for PDF report generation.
"""

from typing import Optional

from pydantic import BaseModel, Field

from app.config import UnitSystem


class ReportInput(BaseModel):
    """Input for generating a PDF report."""

    title: str = "Psychrometric Report"
    unit_system: UnitSystem = UnitSystem.IP
    pressure: float = 14.696
    altitude: float = 0.0
    chart_image_base64: str = Field(
        ..., description="Base64-encoded PNG image of the chart"
    )

    state_points: list[dict] = Field(
        default_factory=list,
        description="List of StatePointOutput dicts",
    )
    processes: list[dict] = Field(
        default_factory=list,
        description="List of ProcessOutput dicts",
    )
    coil_result: Optional[dict] = Field(
        None, description="CoilOutput dict, if present"
    )
    shr_lines: list[dict] = Field(
        default_factory=list,
        description="List of SHRLineOutput dicts",
    )
    gshr_result: Optional[dict] = Field(
        None, description="GSHROutput dict, if present"
    )
    notes: Optional[str] = Field(
        None, description="Free-text notes to include in the report"
    )
    include_sections: list[str] = Field(
        default_factory=lambda: ["chart", "state_points", "processes", "coil", "shr", "notes"],
        description="Which sections to include in the report",
    )
