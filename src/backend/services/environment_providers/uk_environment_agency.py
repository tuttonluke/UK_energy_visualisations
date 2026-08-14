"""
===============================================================================
File: uk_environment_agency.py
Description: Client for fetching river station and reading data from the UK Environment Agency.
Date: 2026-08-14
License: MIT License
===============================================================================
"""

import logging
from typing import Any, Dict, List, Optional

from services.environment_providers.base_environment_provider import (
    BaseEnvironmentProvider,
)
from services.http_client import get_client

logger = logging.getLogger(__name__)


def _parse_stage_scale(scale):
    """Extracts typical range values, handling unexpected API types safely."""
    if isinstance(scale, dict):
        return scale.get("typicalRangeLow"), scale.get("typicalRangeHigh")
    return None, None


def _get_first_if_list(value):
    """The EA API sometimes returns lists instead of scalars for some fields."""
    if isinstance(value, list) and len(value) > 0:
        return value[0]
    return value


def _extract_station_info(item):
    """Extracts and normalizes station attributes into a clean dictionary."""
    typical_low, typical_high = _parse_stage_scale(item.get("stageScale", {}))

    return {
        "stationReference": item.get("stationReference"),
        "label": _get_first_if_list(item.get("label")),
        "riverName": item.get("riverName"),
        "lat": _get_first_if_list(item.get("lat")),
        "long": _get_first_if_list(item.get("long")),
        "typicalRangeLow": typical_low,
        "typicalRangeHigh": typical_high,
    }


def _add_measures_to_cache(item, station_info, cache):
    """Links all measure IDs for a station to its parsed info in the cache."""
    measures = item.get("measures", [])

    # Handle list of measures
    if isinstance(measures, list):
        for measure in measures:
            measure_id = measure.get("@id")
            if measure_id:
                cache[measure_id] = station_info
    # Handle single measure dict
    elif isinstance(measures, dict):
        measure_id = measures.get("@id")
        if measure_id:
            cache[measure_id] = station_info


class EnvironmentAgencyProvider(BaseEnvironmentProvider):
    """
    Fetches river level stations and latest readings from the Environment Agency API.
    """

    def __init__(self):
        super().__init__("environment_agency")

    async def _do_fetch_stations(self) -> Optional[Dict[str, Any]]:
        url = "https://environment.data.gov.uk/flood-monitoring/id/stations?parameter=level&_view=full"
        client = get_client()
        response = await client.get(url, timeout=30.0)
        response.raise_for_status()
        data = response.json()

        new_cache = {}
        for item in data.get("items", []):
            station_info = _extract_station_info(item)
            _add_measures_to_cache(item, station_info, new_cache)

        return new_cache

    async def fetch_stations(self) -> Optional[Dict[str, Any]]:
        return await self._execute_with_retry(
            self._do_fetch_stations, cache_key="stations", max_retries=3, backoff=2.0
        )

    async def _do_fetch_readings(self) -> Optional[List[Dict[str, Any]]]:
        url = "https://environment.data.gov.uk/flood-monitoring/data/readings?latest"
        client = get_client()
        response = await client.get(url, timeout=20.0)
        response.raise_for_status()
        data = response.json()
        return data.get("items", [])

    async def fetch_readings(self) -> Optional[List[Dict[str, Any]]]:
        return await self._execute_with_retry(
            self._do_fetch_readings, cache_key="readings", max_retries=3, backoff=2.0
        )
