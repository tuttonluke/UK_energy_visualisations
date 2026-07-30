import logging
import os

import pandas as pd
from entsoe import EntsoePandasClient

logger = logging.getLogger(__name__)

# Svenska kraftnät (Sweden) Bidding Zones
ZONES = {
    "SE1": "SE_1",
    "SE2": "SE_2",
    "SE3": "SE_3",
    "SE4": "SE_4"
}

async def fetch_sweden_entsoe():
    """
    Fetches real-time solar generation for Sweden's 4 bidding zones
    using the ENTSO-E Transparency Platform API.
    Returns a dictionary mapping Bidding Zone to MW, plus 'totalGen'.
    """
    token = os.getenv("ENTSOE_TOKEN")
    if not token:
        logger.error("ENTSOE_TOKEN not found in environment")
        return None

    try:
        client = EntsoePandasClient(api_key=token)

        start = pd.Timestamp.utcnow() - pd.Timedelta(hours=24)
        end = pd.Timestamp.utcnow()

        data = {}
        total = 0.0
        latest_timestamp = None

        for fe_zone, entsoe_zone in ZONES.items():
            try:
                ts = client.query_generation(entsoe_zone, start=start, end=end)
                if "Solar" in ts.columns:
                    val = ts["Solar"].iloc[-1]
                    idx = ts.index[-1]
                    if isinstance(val, pd.Series):
                        val = val.iloc[0]
                    val = float(val)

                    if pd.isna(val):
                        val = 0.0

                    data[fe_zone] = val
                    total += val
                    
                    if idx is not None:
                        ts_formatted = idx.isoformat()
                        if latest_timestamp is None or ts_formatted > latest_timestamp:
                            latest_timestamp = ts_formatted
                else:
                    data[fe_zone] = None
            except Exception as e:
                logger.error(f"Error fetching {fe_zone} from ENTSO-E: {e}")
                data[fe_zone] = None

        data["totalGen"] = total
        if latest_timestamp:
            data["timestamp"] = latest_timestamp

        if total == 0 and all(v == 0 for v in data.values()):
            logger.warning("No solar generation data found in ENTSO-E response for any Sweden zone.")

        return data

    except Exception as e:
        logger.error(f"ENTSO-E live fetch failed for Sweden: {e}")
        return None
