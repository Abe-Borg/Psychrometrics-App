"""
Top-level API router that aggregates all sub-routers.
"""

from fastapi import APIRouter

from app.api.state_point import router as state_point_router
from app.api.chart_data import router as chart_data_router

router = APIRouter()
router.include_router(state_point_router)
router.include_router(chart_data_router)
