import logging

from services.http_client import get_client

logger = logging.getLogger(__name__)


async def fetch_belgium_live():
    """
    Fetches live regional solar data for Belgium (Flanders, Wallonia, Brussels) from Elia API.
    Uses ods087 (Near real-time). Filters out future forecasts by restricting to datetime <= now.
    """
    url = "https://opendata.elia.be/api/explore/v2.1/catalog/datasets/ods087/records?limit=60&order_by=datetime%20desc&where=datetime%3C%3Dnow()"
    client = get_client()
    try:
        res = await client.get(url, timeout=15.0)
        res.raise_for_status()
        data = res.json()

        records = data.get("results", [])

        # Regions of interest for the macro-level map
        target_regions = ["Flanders", "Wallonia", "Brussels"]
        latest_vals = {}

        for record in records:
            region = record.get("region")
            realtime = record.get("realtime")
            # If realtime is null, it hasn't happened yet, fall back to mostrecentforecast for near-realtime
            val = realtime if realtime is not None else record.get("mostrecentforecast")

            if region in target_regions and region not in latest_vals:
                if val is not None:
                    latest_vals[region] = val

            if len(latest_vals) == len(target_regions):
                break

        # Map Elia names to TopoJSON property names
        region_map = {
            "Flanders": "Flanders",
            "Wallonia": "Région wallonne",
            "Brussels": "Brussels",
        }

        flat_data = {}
        total_gen = 0
        for r, val in latest_vals.items():
            topo_name = region_map.get(r, r)
            flat_data[topo_name] = round(val, 1)
            total_gen += val

        flat_data["totalGen"] = round(total_gen, 1)
        return flat_data
    except Exception as e:
        logger.error(f"Belgium Live fetch failed: {e}")
        return None
