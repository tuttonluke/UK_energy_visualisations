import logging

from services.http_client import get_client

logger = logging.getLogger(__name__)


async def fetch_denmark_live():
    """
    Fetches live regional solar data for Denmark (DK1, DK2) from Energinet API.
    """
    url = "https://api.energidataservice.dk/dataset/ElectricityProdex5MinRealtime?limit=10&sort=Minutes5UTC%20desc"
    client = get_client()
    try:
        res = await client.get(url, timeout=15.0)
        res.raise_for_status()
        data = res.json()

        records = data.get("records", [])

        # The API returns rows per region per hour.
        # We need the most recent valid SolarPower for DK1 and DK2.
        latest_dk1 = None
        latest_dk2 = None
        latest_timestamp = None

        for record in records:
            area = record.get("PriceArea")
            solar = record.get("SolarPower")
            timestamp = record.get("Minutes5UTC")

            if solar is not None:
                if area == "DK1" and latest_dk1 is None:
                    latest_dk1 = solar
                elif area == "DK2" and latest_dk2 is None:
                    latest_dk2 = solar
                
                if timestamp:
                    # Minutes5UTC looks like '2026-07-30T09:35:00'
                    ts_formatted = timestamp + "Z" if not timestamp.endswith("Z") else timestamp
                    if latest_timestamp is None or ts_formatted > latest_timestamp:
                        latest_timestamp = ts_formatted

            if latest_dk1 is not None and latest_dk2 is not None:
                break

        if latest_dk1 is None and latest_dk2 is None:
            logger.warning("Denmark Solar data not found in Energinet response.")
            return None

        dk1_val = latest_dk1 if latest_dk1 is not None else 0
        dk2_val = latest_dk2 if latest_dk2 is not None else 0

        total_gen = dk1_val + dk2_val

        result = {
            "totalGen": round(total_gen, 1),
            "DK1": round(dk1_val, 1),
            "DK2": round(dk2_val, 1),
        }
        if latest_timestamp:
            result["timestamp"] = latest_timestamp
        return result
    except Exception as e:
        logger.error(f"Denmark Live fetch failed: {e}")
        return None
