"""
===============================================================================
File: dependencies.py
Description: Defines dependency injections for FastAPI routes.
Date: 2026-08-14
License: MIT License
===============================================================================
"""

from fastapi import Request
from services.cache_store import CacheStore


def get_solar_stores(request: Request) -> dict:
    return request.app.state.solar_stores


def get_generation_store(request: Request) -> CacheStore:
    return request.app.state.generation_store


def get_river_stations_store(request: Request) -> CacheStore:
    return request.app.state.river_stations_store


def get_river_readings_store(request: Request) -> CacheStore:
    return request.app.state.river_readings_store
