from dependencies import get_cache_manager
from fastapi import APIRouter, Depends, HTTPException, Request
from rate_limiter import limiter
from schemas import RiverLevelsResponse
from services.cache_manager import CacheManager

router = APIRouter()


@router.get("/river_levels", response_model=RiverLevelsResponse)
@limiter.limit("60/minute")
async def get_river_levels(
    request: Request, cache_manager: CacheManager = Depends(get_cache_manager)
):
    stations_map = await cache_manager.get_river_stations()
    readings = await cache_manager.get_river_readings()

    if stations_map is None or readings is None:
        raise HTTPException(
            status_code=503,
            detail="River level data is currently unavailable. Please try again later.",
        )

    results = []
    # Combine readings with station info
    for reading in readings:
        measure_id = reading.get("measure")
        if measure_id and measure_id in stations_map:
            station = stations_map[measure_id]
            # Only include stations with valid coordinates and typical ranges for visualisation
            if (
                station["lat"] is not None
                and station["long"] is not None
                and station["typicalRangeLow"] is not None
                and station["typicalRangeHigh"] is not None
            ):
                results.append(
                    {
                        "measure": measure_id,
                        "value": reading.get("value"),
                        "stationReference": station["stationReference"],
                        "label": station["label"],
                        "riverName": station["riverName"],
                        "lat": station["lat"],
                        "long": station["long"],
                        "typicalRangeLow": station["typicalRangeLow"],
                        "typicalRangeHigh": station["typicalRangeHigh"],
                    }
                )

    return {"data": results}
