import httpx
import time
from fastapi import APIRouter

router = APIRouter()

GENERATION_CACHE = None
LAST_FETCH_TIME = 0
CACHE_TTL = 300  # 5 minutes

async def fetch_generation_summary():
    global GENERATION_CACHE, LAST_FETCH_TIME
    
    if time.time() - LAST_FETCH_TIME < CACHE_TTL and GENERATION_CACHE:
        return GENERATION_CACHE
        
    print("Cache expired. Fetching fresh data from Elexon BMRS API...")
    url = "https://data.elexon.co.uk/bmrs/api/v1/generation/outturn/summary"
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, timeout=10.0)
            response.raise_for_status()
            data = response.json()
            
            GENERATION_CACHE = data
            LAST_FETCH_TIME = time.time()
            print("Live generation data cached successfully.")
        except Exception as e:
            print(f"Failed to fetch generation data: {e}")
            if GENERATION_CACHE:
                return GENERATION_CACHE # Return stale cache if error occurs
            return {"data": []}
            
    return GENERATION_CACHE

@router.get("/summary")
async def get_generation_summary():
    return await fetch_generation_summary()
