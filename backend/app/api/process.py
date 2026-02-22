"""
API routes for psychrometric process calculations.
"""

from fastapi import APIRouter, HTTPException

from app.models.process import ProcessInput, ProcessOutput, ProcessType
from app.engine.processes.sensible import SensibleSolver
from app.engine.processes.cooling_dehum import CoolingDehumSolver
from app.engine.processes.mixing import MixingSolver
from app.engine.processes.humidification import (
    SteamHumidificationSolver,
    AdiabaticHumidificationSolver,
    HeatedWaterHumidificationSolver,
)
from app.engine.processes.evaporative import (
    DirectEvaporativeSolver,
    IndirectEvaporativeSolver,
    IndirectDirectEvaporativeSolver,
)

router = APIRouter(prefix="/api/v1", tags=["process"])

# Solver dispatch table — maps process types to solver instances
_SOLVERS = {
    ProcessType.SENSIBLE_HEATING: SensibleSolver(),
    ProcessType.SENSIBLE_COOLING: SensibleSolver(),
    ProcessType.COOLING_DEHUMIDIFICATION: CoolingDehumSolver(),
    ProcessType.ADIABATIC_MIXING: MixingSolver(),
    ProcessType.STEAM_HUMIDIFICATION: SteamHumidificationSolver(),
    ProcessType.ADIABATIC_HUMIDIFICATION: AdiabaticHumidificationSolver(),
    ProcessType.HEATED_WATER_HUMIDIFICATION: HeatedWaterHumidificationSolver(),
    ProcessType.DIRECT_EVAPORATIVE: DirectEvaporativeSolver(),
    ProcessType.INDIRECT_EVAPORATIVE: IndirectEvaporativeSolver(),
    ProcessType.INDIRECT_DIRECT_EVAPORATIVE: IndirectDirectEvaporativeSolver(),
}


@router.post("/process", response_model=ProcessOutput)
async def calculate_process(data: ProcessInput) -> ProcessOutput:
    """
    Calculate a psychrometric process.

    Dispatches to the appropriate solver based on process_type.
    Returns start state, end state, path points, metadata, and any warnings.
    """
    solver = _SOLVERS.get(data.process_type)
    if solver is None:
        raise HTTPException(
            status_code=422,
            detail=f"Process type '{data.process_type}' is not yet implemented.",
        )

    try:
        return solver.solve(data)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Calculation error: {str(e)}")
