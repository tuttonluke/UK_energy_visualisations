import logging
import urllib.parse
from datetime import timedelta

from services.http_client import get_client

logger = logging.getLogger(__name__)


async def fetch_rte_history(min_dt, max_dt):
    """Fetches national historical solar data for France from ODRE."""
    start_str = min_dt.strftime("%Y-%m-%dT%H:%M:%S")
    end_dt = max_dt + timedelta(minutes=60)
    end_str = end_dt.strftime("%Y-%m-%dT%H:%M:%S")

    where_clause = f"date_heure >= date'{start_str}' and date_heure <= date'{end_str}'"
    query = urllib.parse.urlencode(
        {"limit": 100, "where": where_clause, "order_by": "date_heure ASC"}
    )
    url = f"https://odre.opendatasoft.com/api/explore/v2.1/catalog/datasets/eco2mix-national-tr/records?{query}"

    client = get_client()
    try:
        res = await client.get(url, timeout=10.0)
        res.raise_for_status()
        data = res.json()

        pv_dict = {}
        for record in data.get("results", []):
            timestamp = record.get("date_heure")
            solar_gen = record.get("solaire")
            if timestamp and solar_gen is not None:
                # Opendatasoft returns ISO strings with +00:00, ensure it matches Z or just use as is
                timestamp = timestamp.replace("+00:00", "Z")
                pv_dict[timestamp] = solar_gen
        return pv_dict
    except Exception as e:
        logger.error(f"RTE History fetch failed: {e}")
        return {}


async def fetch_rte_live():
    """Fetches regional live solar data for France from ODRE."""
    url = "https://odre.opendatasoft.com/api/explore/v2.1/catalog/datasets/eco2mix-regional-tr/records?limit=100&order_by=date_heure%20DESC&where=solaire%20is%20not%20null"
    client = get_client()
    try:
        res = await client.get(url, timeout=10.0)
        res.raise_for_status()
        data = res.json()

        new_data = {}
        latest_timestamp = None

        for record in data.get("results", []):
            insee_code = record.get("code_insee_region")
            solar_gen = record.get("solaire")
            timestamp = record.get("date_heure")

            if insee_code and solar_gen is not None and solar_gen >= 0:
                # Keep only the most recent reading for each region
                if insee_code not in new_data:
                    new_data[insee_code] = solar_gen
                if timestamp:
                    # Opendatasoft returns ISO strings with +00:00, ensure it matches Z or just use as is
                    ts_formatted = timestamp.replace("+00:00", "Z")
                    if latest_timestamp is None or ts_formatted > latest_timestamp:
                        latest_timestamp = ts_formatted

        total_generation_mw = sum(new_data.values())
        new_data["totalGen"] = round(total_generation_mw, 1)
        if latest_timestamp:
            new_data["timestamp"] = latest_timestamp
        return new_data
    except Exception as e:
        logger.error(f"RTE Live fetch failed: {e}")
        return None
