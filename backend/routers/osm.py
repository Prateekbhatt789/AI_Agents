from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.osm_fetcher import fetch_pois

router = APIRouter()

# This is a VALIDATOR
class POIRequest(BaseModel):
    lat:       float
    lon:       float
    radius_km: float = 5.0  # fixed for now

@router.post("/fetch-pois")
async def get_pois(request: POIRequest):
    try:
        return fetch_pois(request.lat, request.lon, request.radius_km)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



