from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import geocoding, osm, chat, report,analysis
import logging,sys
from db.database import engine
app = FastAPI(title="GIS AI Agent API")

# 1. Setup the configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s:     %(message)s", # Clean format for terminal
    handlers=[logging.StreamHandler(sys.stdout)] # Forces output to terminal
)

logger = logging.getLogger(__name__)

@app.on_event("startup")
async def check_connection():
    try:
        with engine.connect():
            logger.info("Database Connection successful!")
    except Exception as e:
        logger.info(f"Database Connection failed: {e}")


# Allow requests coming from React
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(geocoding.router, prefix="/api")
app.include_router(osm.router, prefix="/api")
app.include_router(chat.router, prefix="/api")
app.include_router(report.router, prefix="/api")
app.include_router(analysis.router, prefix='/api')


@app.get("/")
def root():
    return {"message": "GIS AI Agent Backend Running"}


import uvicorn

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
