from fastapi import APIRouter, HTTPException

# Pydantic validates incoming data. It ensures the frontend sends the correct data format.
from pydantic import BaseModel

from services.maptiler import geocode

router = APIRouter()

class SearchRequest(BaseModel):
    query: str

@router.post("/search")
async def search(request: SearchRequest):
    try:
        return await geocode(request.query)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))