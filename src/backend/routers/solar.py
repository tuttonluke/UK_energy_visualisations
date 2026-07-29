from dependencies import (
    get_energy_charts_store,
    get_solar_dk_store,
    get_solar_be_store,
    get_solar_fr_store,
    get_solar_uk_store,
    get_solar_it_store,
    get_solar_ie_store,
    get_solar_ni_store,
    get_solar_se_store,
    get_solar_no_store,
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


@router.get("/solar/italy", response_model=SolarResponse)
@limiter.limit("60/minute")
async def get_solar_italy_data(
    request: Request, solar_it_store: CacheStore = Depends(get_solar_it_store)
):
    data = await solar_it_store.get()
    if data is None:
        raise HTTPException(
            status_code=503,
            detail="Italian solar data is currently unavailable. Please try again later.",
        )
    return data


@router.get("/solar/ireland", response_model=SolarResponse)
@limiter.limit("60/minute")
async def get_solar_ireland_data(
    request: Request, solar_ie_store: CacheStore = Depends(get_solar_ie_store)
):
    data = await solar_ie_store.get()
    if data is None:
        raise HTTPException(
            status_code=503,
            detail="Irish solar data is currently unavailable. Please try again later.",
        )
    return data


@router.get("/solar/ni", response_model=SolarResponse)
@limiter.limit("60/minute")
async def get_solar_ni_data(
    request: Request, solar_ni_store: CacheStore = Depends(get_solar_ni_store)
):
    data = await solar_ni_store.get()
    if data is None:
        raise HTTPException(
            status_code=503,
            detail="Northern Irish solar data is currently unavailable. Please try again later.",
        )
    return data


@router.get("/solar/sweden", response_model=SolarResponse)
@limiter.limit("60/minute")
async def get_solar_sweden_data(
    request: Request, solar_se_store: CacheStore = Depends(get_solar_se_store)
):
    data = await solar_se_store.get()
    if data is None:
        raise HTTPException(
            status_code=503,
            detail="Swedish solar data is currently unavailable. Please try again later.",
        )
    return data


@router.get("/solar/norway", response_model=SolarResponse)
@limiter.limit("60/minute")
async def get_solar_norway_data(
    request: Request, solar_no_store: CacheStore = Depends(get_solar_no_store)
):
    data = await solar_no_store.get()
    if data is None:
        raise HTTPException(
            status_code=503,
            detail="Norwegian solar data is currently unavailable. Please try again later.",
        )
    return data
