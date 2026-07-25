import logging

from services.http_client import get_client

logger = logging.getLogger(__name__)


async def fetch_germany_live():
    """Fetches national live solar data for Germany from Energy-Charts API."""
    url = "https://api.energy-charts.info/public_power?country=de"
    client = get_client()
    try:
        res = await client.get(url, timeout=15.0)
        res.raise_for_status()
        data = res.json()

        solar_data_series = None
        unix_seconds_series = data.get("unix_seconds", [])

        # Find the solar generation series
        for series in data.get("production_types", []):
            if series.get("name") == "Solar":
                solar_data_series = series.get("data", [])
                break

        if not solar_data_series or not unix_seconds_series:
            logger.warning("Germany Solar data not found in Energy-Charts response.")
            return None

        latest_value = 0

        for i in range(len(solar_data_series) - 1, -1, -1):
            val = solar_data_series[i]
            if val is not None:
                latest_value = val
                break

        return {"totalGen": round(latest_value, 1)}
    except Exception as e:
        logger.error(f"Germany Live fetch failed: {e}")
        return None
