"""
API routes for chart background data generation.
"""

from fastapi import APIRouter, HTTPException

from app.config import UnitSystem, DEFAULT_PRESSURE_IP, DEFAULT_PRESSURE_SI
from app.engine.chart_generator import generate_chart_data

router = APIRouter(prefix="/api/v1", tags=["chart-data"])


@router.get("/chart-data")
async def get_chart_data(
    unit_system: UnitSystem = UnitSystem.IP,
    pressure: float | None = None,
) -> dict:
    """
    Generate all psychrometric chart background data.

    Returns saturation curve, constant RH lines, constant Twb lines,
    constant enthalpy lines, and constant specific volume lines.

    If pressure is not provided, uses standard sea-level pressure
    for the selected unit system.
    """
    if pressure is None:
        pressure = (
            DEFAULT_PRESSURE_IP
            if unit_system == UnitSystem.IP
            else DEFAULT_PRESSURE_SI
        )

    try:
        data = generate_chart_data(pressure, unit_system)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chart data generation error: {str(e)}")
