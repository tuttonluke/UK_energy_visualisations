import asyncio
import httpx
import time
from fastapi import APIRouter

router = APIRouter()

# Setup memory cache for solar data
SOLAR_CACHE = {}
LAST_FETCH_TIME = 0
CACHE_TTL = 300  # 5 minutes

async def fetch_PES_region_data(client: httpx.AsyncClient, pes_id: int):
    """Fetch data for singly PES region asynchronously"""
    url = f"https://api.pvlive.uk/pvlive/api/v4/pes/{pes_id}"
    try:
        response = await client.get(url, timeout=5.0)
        response.raise_for_status()  # Raises an exception for 4xx/5xx errors
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
    print("Live data cached successfully.")

    return SOLAR_CACHE

@router.get("/solar")
async def get_solar():
    return await get_live_solar_data()
