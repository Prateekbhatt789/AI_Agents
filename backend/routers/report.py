from fastapi import APIRouter
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Dict, Any
from services.pdf_report import generate_pdf

router = APIRouter()

class ReportRequest(BaseModel):
    location:     str
    lat:          float
    lon:          float
    radius_km:    float
    summary:      Dict[str, Any]
    suggestions:  List[Dict[str, Any]] = []   # optional
    road_summary: Dict[str, Any]       = {}   # optional

@router.post("/export-pdf")
async def export_pdf(request: ReportRequest):
    path = generate_pdf(
        location     = request.location,
        lat          = request.lat,
        lon          = request.lon,
        radius_km    = request.radius_km,
        summary      = request.summary,
        suggestions  = request.suggestions,
        road_summary = request.road_summary,
    )
    return FileResponse(
        path,
        media_type       = "application/pdf",
        filename         = "site_report.pdf",
        headers          = {"Content-Disposition": "attachment; filename=site_report.pdf"}
    )