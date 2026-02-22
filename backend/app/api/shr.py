"""
API routes for SHR (Sensible Heat Ratio) line calculations.
"""

from fastapi import APIRouter, HTTPException

from app.models.shr import SHRLineInput, SHRLineOutput, GSHRInput, GSHROutput
from app.engine.shr import calculate_shr_line, calculate_gshr

router = APIRouter(prefix="/api/v1/shr", tags=["shr"])


@router.post("/line", response_model=SHRLineOutput)
async def shr_line(data: SHRLineInput) -> SHRLineOutput:
    """
    Calculate an SHR line through a room state point.

    Returns the line points, slope, and ADP (intersection with saturation curve).
    """
    try:
        return calculate_shr_line(data)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Calculation error: {str(e)}")


@router.post("/gshr", response_model=GSHROutput)
async def gshr_calculation(data: GSHRInput) -> GSHROutput:
    """
    Calculate Grand SHR (GSHR) and optionally Effective SHR (ESHR).

    Returns room SHR, GSHR, ESHR, corresponding SHR lines, and ADP intersections.
    """
    try:
        return calculate_gshr(data)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Calculation error: {str(e)}")
