from fastapi import APIRouter
from fastapi.responses import FileResponse
from pydantic import BaseModel
from services.pdf_report import generate_pdf

router = APIRouter()

class ReportRequest(BaseModel):
    location:  str
    lat:       float
    lon:       float
    radius_km: float
    summary:   dict

@router.post("/export-pdf")
async def export_pdf(request: ReportRequest):
    path = generate_pdf(request.location, request.lat, request.lon, request.radius_km, request.summary)
    return FileResponse(path, media_type="application/pdf", filename="site_report.pdf")