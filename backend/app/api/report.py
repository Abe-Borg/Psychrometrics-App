"""
API route for PDF report generation.
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from app.models.report import ReportInput
from app.engine.report_generator import generate_report

router = APIRouter(prefix="/api/v1", tags=["report"])


@router.post("/report/generate")
async def create_report(body: ReportInput) -> Response:
    """Generate a PDF report and return it as a downloadable file."""
    try:
        pdf_bytes = bytes(generate_report(body))
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{body.title}.pdf"',
            },
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
