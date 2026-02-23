"""
API routes for weather data processing (TMY3 CSV and EPW files).
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Query

from app.config import UnitSystem, DEFAULT_PRESSURE_IP, DEFAULT_PRESSURE_SI
from app.engine.tmy_processor import parse_tmy3, parse_epw
from app.models.tmy import TMYProcessOutput

router = APIRouter(prefix="/api/v1", tags=["tmy"])

ALLOWED_EXTENSIONS = (".csv", ".epw")


@router.post("/tmy/upload", response_model=TMYProcessOutput)
async def upload_tmy_file(
    file: UploadFile = File(...),
    unit_system: UnitSystem = Query("IP"),
    pressure: float = Query(DEFAULT_PRESSURE_IP),
):
    """
    Upload a TMY3 CSV or EPW weather file and get processed scatter + heatmap data.
    """
    filename = (file.filename or "").lower()
    if not any(filename.endswith(ext) for ext in ALLOWED_EXTENSIONS):
        raise HTTPException(
            status_code=400,
            detail="File must be a .csv or .epw file.",
        )

    try:
        content = await file.read()
        text = content.decode("utf-8", errors="replace")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not read file: {e}")

    try:
        if filename.endswith(".epw"):
            result = parse_epw(
                file_content=text,
                unit_system=unit_system,
                pressure=pressure,
            )
        else:
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
