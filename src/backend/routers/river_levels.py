import httpx
import time
import asyncio
from fastapi import APIRouter

router = APIRouter()

# Caches
STATIONS_CACHE = {}
LAST_STATIONS_FETCH_TIME = 0
STATIONS_CACHE_TTL = 86400  # 24 hours for station metadata

READINGS_CACHE = {}
LAST_READINGS_FETCH_TIME = 0
READINGS_CACHE_TTL = 300  # 5 minutes for readings

async def fetch_stations():
    global STATIONS_CACHE, LAST_STATIONS_FETCH_TIME
    if time.time() - LAST_STATIONS_FETCH_TIME < STATIONS_CACHE_TTL and STATIONS_CACHE:
        return STATIONS_CACHE

    print("Fetching EA Stations...")
    url = "https://environment.data.gov.uk/flood-monitoring/id/stations?parameter=level&_view=full"
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, timeout=30.0)
            response.raise_for_status()
            data = response.json()
            
            # Map station measure IDs to station info for quick lookup
            new_cache = {}
            for item in data.get("items", []):
                # Look for the stageScale typical ranges
                scale = item.get("stageScale", {})
                if isinstance(scale, dict):
                    typical_low = scale.get("typicalRangeLow")
                    typical_high = scale.get("typicalRangeHigh")
                else:
                    typical_low = None
                    typical_high = None

                station_info = {
                    "stationReference": item.get("stationReference"),
                    "label": item.get("label"),
                    "riverName": item.get("riverName"),
                    "lat": item.get("lat"),
                    "long": item.get("long"),
                    "typicalRangeLow": typical_low,
                    "typicalRangeHigh": typical_high
                }
                
                # A station can have multiple measures. We key by measure URL so we can match with readings
                measures = item.get("measures", [])
                if isinstance(measures, list):
                    for measure in measures:
                        measure_id = measure.get("@id")
                        if measure_id:
                            new_cache[measure_id] = station_info
                elif isinstance(measures, dict):
                    measure_id = measures.get("@id")
                    if measure_id:
                        new_cache[measure_id] = station_info

            STATIONS_CACHE = new_cache
            LAST_STATIONS_FETCH_TIME = time.time()
            print(f"Cached {len(STATIONS_CACHE)} station measures.")
        except Exception as e:
            print(f"Failed to fetch stations: {e}")
    return STATIONS_CACHE

async def fetch_latest_readings():
    global READINGS_CACHE, LAST_READINGS_FETCH_TIME
    if time.time() - LAST_READINGS_FETCH_TIME < READINGS_CACHE_TTL and READINGS_CACHE:
        return READINGS_CACHE

    print("Fetching EA Readings...")
    url = "https://environment.data.gov.uk/flood-monitoring/data/readings?latest"
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, timeout=20.0)
            response.raise_for_status()
            data = response.json()
            READINGS_CACHE = data.get("items", [])
            LAST_READINGS_FETCH_TIME = time.time()
            print(f"Cached {len(READINGS_CACHE)} readings.")
        except Exception as e:
            print(f"Failed to fetch readings: {e}")
    return READINGS_CACHE

@router.get("/river_levels")
async def get_river_levels():
    # Fetch both concurrently
    stations_task = asyncio.create_task(fetch_stations())
    readings_task = asyncio.create_task(fetch_latest_readings())
    
    stations_map, readings = await asyncio.gather(stations_task, readings_task)
    
    results = []
    # Combine readings with station info
    for reading in readings:
        measure_id = reading.get("measure")
        if measure_id and measure_id in stations_map:
            station = stations_map[measure_id]
            # Only include stations with valid coordinates and typical ranges for visualisation
            if station["lat"] is not None and station["long"] is not None and station["typicalRangeLow"] is not None and station["typicalRangeHigh"] is not None:
                results.append({
                    "measure": measure_id,
                    "value": reading.get("value"),
                    "stationReference": station["stationReference"],
                    "label": station["label"],
                    "riverName": station["riverName"],
                    "lat": station["lat"],
                    "long": station["long"],
                    "typicalRangeLow": station["typicalRangeLow"],
                    "typicalRangeHigh": station["typicalRangeHigh"]
                })
    
    return {"data": results}
