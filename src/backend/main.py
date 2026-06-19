import asyncio
import httpx
import json
import os
import time
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

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
    STATIC_GEOJSON_DATA = {"error": "regions_wgs84.geojson file not found."}

# Setup memory cache for solar data
SOLAR_CACHE = {}
LAST_FETCH_TIME = 0
CACHE_TTL = 300 # 5 minutes

# async lock
CACHE_LOCK = asyncio.Lock()

async def fetch_PES_region_data(client: httpx.AsyncClient, pes_id: int):
    """Fetch data for singly PES region asynchronously"""
    url = f"https://api.pvlive.uk/pvlive/api/v4/pes/{pes_id}"
    try:
        response = await client.get(url, timeout = 0.5)
        response.raise_for_status() # Raises an exception for 4xx/5xx errors
        data = response.json()

        if data.get("data") and len(data["data"]) > 0:
            return str(pes_id), data["data"][0][2]
    except Exception as e:
        print(f"Failed to fetch data for PES {pes_id}: {e}")

    return str(pes_id), 0

async def get_live_solar_data():
    global SOLAR_CACHE, LAST_FETCH_TIME

    if time.time() - LAST_FETCH_TIME < CACHE_TTL and SOLAR_CACHE:
        return SOLAR_CACHE
    
    print("Cache expired. Fetching fresh data from PV_Live API...")
    new_data = {}
    total_generation_mw = 0

    async with httpx.AsyncClient() as client:
        # GB's 14 PES regions are numbered 10-23
        tasks = [fetch_PES_region_data(client, pes_id) for pes_id in range(10, 24)]
        results = await asyncio.gather(*tasks)
    
    for pes_id_str, generation in results:
        if generation > 0:
            new_data[pes_id_str] = generation
            total_generation_mw += generation

    new_data["total_gen"] = round(total_generation_mw, 1)
    SOLAR_CACHE = new_data
    LAST_FETCH_TIME = time.time()
    print ("Live data cached successfully.")

    return SOLAR_CACHE

# API endpoints
@app.get("/api/config")
def get_config():
    token = os.getenv("MAPBOX_ACCESS_TOKEN")
    return {"mapboxToken": token}

@app.get("/api/regions")
def get_regions():
    return JSONResponse(content=STATIC_GEOJSON_DATA)

@app.get("/api/solar")
async def get_solar():
    return await get_live_solar_data()
    
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
