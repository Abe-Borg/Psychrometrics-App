"""
API routes for TMY (Typical Meteorological Year) data processing.
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Query

from app.config import UnitSystem, DEFAULT_PRESSURE_IP, DEFAULT_PRESSURE_SI
from app.engine.tmy_processor import parse_tmy3
from app.models.tmy import TMYProcessOutput

router = APIRouter(prefix="/api/v1", tags=["tmy"])


@router.post("/tmy/upload", response_model=TMYProcessOutput)
async def upload_tmy_file(
    file: UploadFile = File(...),
    unit_system: UnitSystem = Query("IP"),
    pressure: float = Query(DEFAULT_PRESSURE_IP),
):
    """
    Upload a TMY3 CSV file and get processed scatter + heatmap data.
    """
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="File must be a .csv file.")

    try:
        content = await file.read()
        text = content.decode("utf-8", errors="replace")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not read file: {e}")

    try:
        result = parse_tmy3(
            file_content=text,
            unit_system=unit_system,
            pressure=pressure,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
