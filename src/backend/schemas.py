"""
===============================================================================
File: schemas.py
Description: Pydantic models for request and response validation.
Date: 2026-08-14
License: MIT License
===============================================================================
"""

from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict


# Generation Models
class FuelData(BaseModel):
    fuelType: str
    generation: float


class GenerationPeriod(BaseModel):
    startTime: str
    data: List[FuelData]


class SolarResponse(BaseModel):
    totalGen: Dict[str, float]
    timestamp: Optional[str] = None

    model_config = ConfigDict(extra="allow")


# River Levels Models
class RiverStationData(BaseModel):
    measure: str
    value: Optional[float] = None
    stationReference: str
    label: str
    riverName: Optional[str] = None
    lat: float
    long: float
    typicalRangeLow: float
    typicalRangeHigh: float


class RiverLevelsResponse(BaseModel):
    data: List[RiverStationData]
