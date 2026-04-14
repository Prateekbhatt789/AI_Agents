from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import geocoding, osm, chat, report

app = FastAPI(title="GIS AI Agent API")

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


@app.get("/")
def root():
    return {"message": "GIS AI Agent Backend Running"}


import uvicorn

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
