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

        for record in records:
            area = record.get("PriceArea")
            solar = record.get("SolarPower")

            if solar is not None:
                if area == "DK1" and latest_dk1 is None:
                    latest_dk1 = solar
                elif area == "DK2" and latest_dk2 is None:
                    latest_dk2 = solar

            if latest_dk1 is not None and latest_dk2 is not None:
                break

        if latest_dk1 is None and latest_dk2 is None:
            logger.warning("Denmark Solar data not found in Energinet response.")
            return None

        dk1_val = latest_dk1 if latest_dk1 is not None else 0
        dk2_val = latest_dk2 if latest_dk2 is not None else 0

        total_gen = dk1_val + dk2_val

        return {
            "totalGen": round(total_gen, 1),
            "DK1": round(dk1_val, 1),
            "DK2": round(dk2_val, 1),
        }
    except Exception as e:
        logger.error(f"Denmark Live fetch failed: {e}")
        return None
