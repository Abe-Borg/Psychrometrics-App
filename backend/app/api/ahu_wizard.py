"""
API routes for the AHU Wizard.
"""

from fastapi import APIRouter, HTTPException

from app.models.ahu_wizard import AHUWizardInput, AHUWizardOutput
from app.engine.ahu_wizard import calculate_ahu

router = APIRouter(prefix="/api/v1", tags=["ahu-wizard"])


@router.post("/ahu-wizard", response_model=AHUWizardOutput)
async def run_ahu_wizard(body: AHUWizardInput) -> AHUWizardOutput:
    """Run the AHU wizard calculation."""
    try:
        return calculate_ahu(body)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
