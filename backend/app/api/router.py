"""
Top-level API router that aggregates all sub-routers.
"""

from fastapi import APIRouter

from app.api.state_point import router as state_point_router
from app.api.chart_data import router as chart_data_router
from app.api.process import router as process_router
from app.api.coil import router as coil_router
from app.api.shr import router as shr_router
from app.api.airflow import router as airflow_router

router = APIRouter()
router.include_router(state_point_router)
router.include_router(chart_data_router)
router.include_router(process_router)
router.include_router(coil_router)
router.include_router(shr_router)
router.include_router(airflow_router)
