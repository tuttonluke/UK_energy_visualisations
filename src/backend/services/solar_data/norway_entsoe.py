import logging
import os

import pandas as pd
from entsoe import EntsoePandasClient

logger = logging.getLogger(__name__)

# Statnett (Norway) Bidding Zones
ZONES = {
    "NO1": "NO_1",
    "NO2": "NO_2",
    "NO3": "NO_3",
    "NO4": "NO_4",
    "NO5": "NO_5"
}

async def fetch_norway_entsoe():
    """
    Fetches real-time solar generation for Norway's 5 bidding zones
    using the ENTSO-E Transparency Platform API.
    Returns a dictionary mapping Bidding Zone to MW, plus 'totalGen'.
    """
    token = os.getenv("ENTSOE_TOKEN")
    if not token:
        logger.error("ENTSOE_TOKEN not found in environment")
        return None

    try:
        client = EntsoePandasClient(api_key=token)

        start = pd.Timestamp.utcnow() - pd.Timedelta(hours=2)
        end = pd.Timestamp.utcnow()

        data = {}
        total = 0.0

        for fe_zone, entsoe_zone in ZONES.items():
            try:
                ts = client.query_generation(entsoe_zone, start=start, end=end)
                if "Solar" in ts.columns:
                    val = ts["Solar"].iloc[-1]
                    if isinstance(val, pd.Series):
                        val = val.iloc[0]
                    val = float(val)

                    if pd.isna(val):
                        val = 0.0

                    data[fe_zone] = val
                    total += val
                else:
                    data[fe_zone] = 0.0
            except Exception as e:
                logger.error(f"Error fetching {fe_zone} from ENTSO-E: {e}")
                data[fe_zone] = 0.0

        data["totalGen"] = total

        if total == 0 and all(v == 0 for v in data.values()):
            logger.warning("No solar generation data found in ENTSO-E response for any Norway zone.")

        return data

    except Exception as e:
        logger.error(f"ENTSO-E live fetch failed for Norway: {e}")
        return None
