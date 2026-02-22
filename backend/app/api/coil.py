"""
API routes for coil analysis calculations.
"""

from fastapi import APIRouter, HTTPException

from app.models.coil import CoilInput, CoilOutput
from app.engine.coil import analyze_coil

router = APIRouter(prefix="/api/v1", tags=["coil"])


@router.post("/coil", response_model=CoilOutput)
async def coil_analysis(data: CoilInput) -> CoilOutput:
    """
    Perform coil analysis.

    Forward mode: entering conditions + ADP + BF → leaving conditions + loads.
    Reverse mode: entering + leaving conditions → ADP + BF + loads.

    Optionally provide airflow for absolute load calculations and
    water temperatures for GPM estimation.
    """
    try:
        return analyze_coil(data)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Calculation error: {str(e)}")
