from dependencies import get_solar_fr_store, get_solar_uk_store
from fastapi import APIRouter, Depends, HTTPException, Request
from rate_limiter import limiter
from schemas import SolarResponse
from services.cache_store import CacheStore

router = APIRouter()


@router.get("/solar", response_model=SolarResponse)
@limiter.limit("60/minute")
async def get_solar_data(
    request: Request, solar_uk_store: CacheStore = Depends(get_solar_uk_store)
):
    data = await solar_uk_store.get()
    if data is None:
        raise HTTPException(
            status_code=503,
            detail="Solar data is currently unavailable. Please try again later.",
        )
    return data


@router.get("/solar/france", response_model=SolarResponse)
@limiter.limit("60/minute")
async def get_solar_france_data(
    request: Request, solar_fr_store: CacheStore = Depends(get_solar_fr_store)
):
    data = await solar_fr_store.get()
    if data is None:
        raise HTTPException(
            status_code=503,
            detail="French solar data is currently unavailable. Please try again later.",
        )
    return data
