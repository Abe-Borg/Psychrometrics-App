"""
API routes for weather data analysis (EPW clustering + design point extraction).
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Query

from app.config import UnitSystem
from app.engine.weather_analysis.design_extractor import extract_design_conditions
from app.models.weather_analysis import WeatherAnalysisOutput

router = APIRouter(prefix="/api/v1", tags=["weather-analysis"])


@router.post("/weather/analyze", response_model=WeatherAnalysisOutput)
async def analyze_weather_file(
    file: UploadFile = File(...),
    n_clusters: int = Query(5, ge=2, le=10),
    unit_system: UnitSystem = Query("IP"),
):
    """
    Upload an EPW weather file, cluster the hourly data, and extract
    extreme + cluster worst-case design condition points.
    """
    filename = (file.filename or "").lower()
    if not filename.endswith(".epw"):
        raise HTTPException(
            status_code=400,
            detail="File must be an .epw file.",
        )

    try:
        content = await file.read()
        text = content.decode("utf-8", errors="replace")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not read file: {e}")

    try:
        result = extract_design_conditions(
            epw_content=text,
            n_clusters=n_clusters,
            unit_system=unit_system,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
