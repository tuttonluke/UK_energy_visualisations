import asyncio
import logging

from services.http_client import get_client

logger = logging.getLogger(__name__)

# List of countries to fetch from Fraunhofer Energy-Charts
# 'ch': Switzerland, 'pl': Poland, 'cz': Czechia, 'es': Spain
COUNTRIES = ["de", "nl", "at", "ch", "pl", "cz", "es"]


async def fetch_energy_charts_live():
    """
    Fetches national live solar data for multiple countries from Energy-Charts API.
    Fetches sequentially with a delay to avoid 429 Too Many Requests.
    """
    client = get_client()
    results = {}

    for i, country in enumerate(COUNTRIES):
        if i > 0:
            # Respect API rate limits (strictly 1 req/sec limit)
            await asyncio.sleep(1.5)

        url = f"https://api.energy-charts.info/public_power?country={country}"

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
                logger.warning(
                    f"Solar data not found in Energy-Charts response for {country}."
                )
                results[country] = None
                continue

            latest_value = 0

            # Scan backwards for the latest non-null value
            for j in range(len(solar_data_series) - 1, -1, -1):
                val = solar_data_series[j]
                if val is not None:
                    latest_value = val
                    break

            results[country] = {"totalGen": round(latest_value, 1)}

        except Exception as e:
            logger.error(f"Energy-Charts Live fetch failed for {country}: {e}")
            results[country] = None

    return results
