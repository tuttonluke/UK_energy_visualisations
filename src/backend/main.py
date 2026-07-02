import json
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

from routers import solar, generation

load_dotenv()
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load static map data
try:
    with open("gb-dno-license-areas-2024_wgs84.geojson", "r") as f:
        STATIC_GEOJSON_DATA = json.load(f)
except FileNotFoundError:
    STATIC_GEOJSON_DATA = {"error": "gb-dno-license-areas-2024_wgs84.geojson file not found."}

# Include routers
app.include_router(solar.router, prefix="/api/solar", tags=["solar"])
app.include_router(generation.router, prefix="/api/generation", tags=["generation"])

# API endpoints
@app.get("/api/config")
def get_config():
    token = os.getenv("MAPBOX_ACCESS_TOKEN")
    return {"mapboxToken": token}

@app.get("/api/regions")
def get_regions():
    return JSONResponse(content=STATIC_GEOJSON_DATA)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
