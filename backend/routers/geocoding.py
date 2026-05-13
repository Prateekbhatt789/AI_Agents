from fastapi import APIRouter, Depends, HTTPException

# Pydantic validates incoming data. It ensures the frontend sends the correct data format.
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from requests import Session
from sqlalchemy import text

from db.session import get_db
from services.maptiler import geocode
from .osm import POIRequest

router = APIRouter()

class SearchRequest(BaseModel):
    query: str

@router.post("/search")
async def search(request: SearchRequest):
    try:
        return await geocode(request.query)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    
@router.post("/fetch-roads")
async def fetch_roads(request: POIRequest, db: Session = Depends(get_db)):
    try:
        latitude = request.lat
        longitude = request.lon
        radius_m = request.radius_km * 1000

        query = text("""
            WITH search_area AS (
                SELECT ST_Buffer(
                    ST_SetSRID(
                        ST_MakePoint(:longitude, :latitude),
                        4326
                    )::geography,
                    :radius_m
                )::geometry AS geom
            )
            SELECT r."id",r."ALT_NAME",r."TYPE",
                ST_AsGeoJSON(ST_Intersection(r.geom, s.geom))::json AS geometry
            FROM "data".road_network_ml r
            JOIN search_area s
                ON ST_Intersects(r.geom, s.geom);
        """)

        params = {
            "longitude": longitude,
            "latitude": latitude,
            "radius_m": radius_m
        }

       
        result = db.execute(query, params)
        rows = result.mappings().all()

        geojson = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": row["geometry"],
                    "properties": {
                        "id": row["id"],
                        "road_name": row.get("road_name"),
                        "highway": row.get("highway"),
                    },
                }
                for row in rows
            ],
        }

        return JSONResponse(content=geojson)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))