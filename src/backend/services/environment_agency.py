import logging

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


async def fetch_ea_stations():
    url = "https://environment.data.gov.uk/flood-monitoring/id/stations?parameter=level&_view=full"
    client = get_client()
    try:
        response = await client.get(url, timeout=30.0)
        response.raise_for_status()
        data = response.json()

        new_cache = {}
        for item in data.get("items", []):
            station_info = _extract_station_info(item)
            _add_measures_to_cache(item, station_info, new_cache)

        return new_cache
    except Exception as e:
        logger.error(f"Failed to fetch stations: {e}")
        return None


async def fetch_ea_readings():
    url = "https://environment.data.gov.uk/flood-monitoring/data/readings?latest"
    client = get_client()
    try:
        response = await client.get(url, timeout=20.0)
        response.raise_for_status()
        data = response.json()
        return data.get("items", [])
    except Exception as e:
        logger.error(f"Failed to fetch readings: {e}")
        return None
