import logging
import urllib.parse
from datetime import datetime, timedelta

from services.http_client import get_client

logger = logging.getLogger(__name__)


def parse_neso_datetime(date_str: str, time_str: str) -> datetime:
    """
    Safely parse the NESO date and time strings.
    Handles '24:00' by rolling over to the next day, and pads short time strings.
    """
    if not date_str or not time_str:
        raise ValueError("date_str and time_str must be provided")

    d_str = date_str.strip().split("T")[0]
    t_str = time_str.strip()

    if t_str == "24:00" or t_str == "24:00:00":
        t_str = "00:00"
        return datetime.fromisoformat(f"{d_str}T{t_str}+00:00") + timedelta(days=1)

    # Pad short times like "9:30" -> "09:30"
    if len(t_str) == 4 and t_str[1] == ":":
        t_str = "0" + t_str

    # Ensure seconds are present
    if len(t_str) == 5:
        t_str += ":00"

    try:
        return datetime.fromisoformat(f"{d_str}T{t_str}+00:00")
    except ValueError as e:
        raise ValueError(f"Could not parse NESO datetime: {d_str}T{t_str}") from e


async def fetch_neso_embedded_wind(min_date):
    datasets = [
        "db6c038f-98af-4570-ab60-24d71ebd0ae5",  # Live
        "31861619-0b86-47ba-bac2-d008a760af54",  # Archive 2026 H2
    ]

    date_str = min_date.strftime("%Y-%m-%d")
    neso_dict = {}

    client = get_client()
    for dataset_id in datasets:
        sql = f'SELECT "DATE_GMT", "TIME_GMT", "EMBEDDED_WIND_FORECAST" FROM "{dataset_id}" WHERE "DATE_GMT" >= \'{date_str}\' LIMIT 2000'
        url = f"https://api.neso.energy/api/3/action/datastore_search_sql?sql={urllib.parse.quote(sql)}"

        try:
            res = await client.get(url, timeout=10.0)
            if res.status_code == 200:
                data = res.json()
                for row in data.get("result", {}).get("records", []):
                    try:
                        dt = parse_neso_datetime(row["DATE_GMT"], row["TIME_GMT"])
                        dt_iso = dt.strftime("%Y-%m-%dT%H:%M:%SZ")
                        neso_dict[dt_iso] = row["EMBEDDED_WIND_FORECAST"]
                    except ValueError as e:
                        logger.warning(f"Skipping row due to parsing error: {e}")
        except Exception as e:
            logger.error(f"NESO fetch failed for {dataset_id}: {e}")

    return neso_dict
