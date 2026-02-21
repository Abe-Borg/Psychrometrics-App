"""
API routes for state point resolution.
"""

from fastapi import APIRouter, HTTPException

from app.models.state_point import StatePointInput, StatePointOutput
from app.engine.state_resolver import resolve_state_point, get_pressure_from_altitude
from app.config import UnitSystem

router = APIRouter(prefix="/api/v1", tags=["state-point"])


@router.post("/state-point", response_model=StatePointOutput)
async def create_state_point(data: StatePointInput) -> StatePointOutput:
    """
    Resolve a full psychrometric state point from two independent properties.

    Accepts any supported input pair (e.g., Tdb+RH, Tdb+Twb, Tdb+Tdp, etc.)
    and returns all psychrometric properties.
    """
    try:
        result = resolve_state_point(
            input_pair=data.input_pair,
            values=data.values,
            pressure=data.pressure,
            unit_system=data.unit_system,
            label=data.label,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Calculation error: {str(e)}")


@router.get("/pressure-from-altitude")
async def pressure_from_altitude(
    altitude: float, unit_system: UnitSystem = UnitSystem.IP
) -> dict:
    """
    Convert altitude to atmospheric pressure.

    Args:
        altitude: Altitude in feet (IP) or meters (SI)
        unit_system: IP or SI

    Returns:
        Atmospheric pressure in psia (IP) or Pa (SI)
    """
    try:
        pressure = get_pressure_from_altitude(altitude, unit_system)
        return {"altitude": altitude, "pressure": round(pressure, 6), "unit_system": unit_system}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Calculation error: {str(e)}")
