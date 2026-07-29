from fastapi import Request
from services.cache_store import CacheStore


def get_solar_uk_store(request: Request) -> CacheStore:
    return request.app.state.solar_uk_store


def get_solar_fr_store(request: Request) -> CacheStore:
    return request.app.state.solar_fr_store


def get_energy_charts_store(request: Request) -> CacheStore:
    return request.app.state.energy_charts_store


def get_solar_dk_store(request: Request) -> CacheStore:
    return request.app.state.solar_dk_store


def get_solar_be_store(request: Request) -> CacheStore:
    return request.app.state.solar_be_store


def get_generation_store(request: Request) -> CacheStore:
    return request.app.state.generation_store


def get_river_stations_store(request: Request) -> CacheStore:
    return request.app.state.river_stations_store


def get_river_readings_store(request: Request) -> CacheStore:
    return request.app.state.river_readings_store


def get_solar_it_store(request: Request) -> CacheStore:
    return request.app.state.solar_it_store


def get_solar_ie_store(request: Request) -> CacheStore:
    return request.app.state.solar_ie_store


def get_solar_ni_store(request: Request) -> CacheStore:
    return request.app.state.solar_ni_store

def get_solar_se_store(request: Request) -> CacheStore:
    return request.app.state.solar_se_store

def get_solar_no_store(request: Request) -> CacheStore:
    return request.app.state.solar_no_store
