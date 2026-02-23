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
from app.api.design_day import router as design_day_router
from app.api.tmy import router as tmy_router
from app.api.ahu_wizard import router as ahu_wizard_router
from app.api.report import router as report_router
from app.api.weather_analysis import router as weather_analysis_router

router = APIRouter()
router.include_router(state_point_router)
router.include_router(chart_data_router)
router.include_router(process_router)
router.include_router(coil_router)
router.include_router(shr_router)
router.include_router(airflow_router)
router.include_router(design_day_router)
router.include_router(tmy_router)
router.include_router(ahu_wizard_router)
router.include_router(report_router)
router.include_router(weather_analysis_router)
