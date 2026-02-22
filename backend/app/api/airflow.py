"""
API routes for airflow and energy calculations.
"""

from fastapi import APIRouter, HTTPException

from app.models.airflow import (
    AirflowCalcInput,
    AirflowCalcOutput,
    CondensationCheckInput,
    CondensationCheckOutput,
)
from app.engine.airflow import calculate_airflow, check_condensation

router = APIRouter(prefix="/api/v1", tags=["airflow"])


@router.post("/airflow-calc", response_model=AirflowCalcOutput)
async def airflow_calc(data: AirflowCalcInput) -> AirflowCalcOutput:
    """
    Calculate airflow, heat load, or delta using the standard HVAC load equations.

    Provide two of three values (Q, airflow, delta) and the third is solved.
    Supports altitude-corrected C-factors via optional reference conditions.
    """
    try:
        return calculate_airflow(data)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Calculation error: {str(e)}")


@router.post("/condensation-check", response_model=CondensationCheckOutput)
async def condensation_check(data: CondensationCheckInput) -> CondensationCheckOutput:
    """
    Check if condensation would occur on a surface at a given temperature.

    Resolves the air state from the provided input pair and compares the
    dew point against the surface temperature.
    """
    try:
        return check_condensation(data)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Calculation error: {str(e)}")
