from dependencies import (
    get_energy_charts_store,
    get_solar_dk_store,
    get_solar_be_store,
    get_solar_fr_store,
    get_solar_uk_store,
)
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


@router.get("/solar/energy_charts")
@limiter.limit("60/minute")
async def get_energy_charts_data(
    request: Request, energy_charts_store: CacheStore = Depends(get_energy_charts_store)
):
    data = await energy_charts_store.get()
    if data is None:
        raise HTTPException(
            status_code=503,
            detail="Energy-Charts solar data is currently unavailable. Please try again later.",
        )
    return data


@router.get("/solar/denmark", response_model=SolarResponse)
@limiter.limit("60/minute")
async def get_solar_denmark_data(
    request: Request, solar_dk_store: CacheStore = Depends(get_solar_dk_store)
):
    data = await solar_dk_store.get()
    if data is None:
        raise HTTPException(
            status_code=503,
            detail="Danish solar data is currently unavailable. Please try again later.",
        )
    return data


@router.get("/solar/belgium", response_model=SolarResponse)
@limiter.limit("60/minute")
async def get_solar_belgium_data(
    request: Request, solar_be_store: CacheStore = Depends(get_solar_be_store)
):
    data = await solar_be_store.get()
    if data is None:
        raise HTTPException(
            status_code=503,
            detail="Belgian solar data is currently unavailable. Please try again later.",
        )
    return data



