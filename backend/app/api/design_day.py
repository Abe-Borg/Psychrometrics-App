"""
API routes for ASHRAE design day conditions.
"""

from fastapi import APIRouter, HTTPException, Query

from app.config import UnitSystem
from app.engine.design_day import search_locations, resolve_design_conditions
from app.models.design_day import (
    DesignDaySearchResult,
    DesignDayResolveInput,
    DesignDayResolveOutput,
)

router = APIRouter(prefix="/api/v1", tags=["design-day"])


@router.get("/design-days/search", response_model=list[DesignDaySearchResult])
def search_design_day_locations(
    q: str = Query("", description="Search query (city name or state)"),
    limit: int = Query(20, ge=1, le=100),
):
    """Search for locations in the design day database."""
    results = search_locations(q, limit=limit)
    return [
        DesignDaySearchResult(
            name=loc["name"],
            state=loc["state"],
            country=loc["country"],
            climate_zone=loc["climate_zone"],
            elevation_ft=loc["elevation_ft"],
        )
        for loc in results
    ]


@router.post("/design-days/resolve", response_model=DesignDayResolveOutput)
def resolve_design_day(body: DesignDayResolveInput):
    """Resolve design day conditions to full psychrometric state points."""
    try:
        result = resolve_design_conditions(
            location_name=body.location_name,
            location_state=body.location_state,
            condition_labels=body.condition_labels,
            unit_system=body.unit_system,
            pressure_override=body.pressure,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
