import asyncio
import logging

from services.http_client import close_client
from services.solar_data.germany_energy_charts import fetch_germany_live

logging.basicConfig(level=logging.INFO)


async def main():
    print("Testing Germany Live...")
    data = await fetch_germany_live()
    print("Data:", data)
    await close_client()


if __name__ == "__main__":
    asyncio.run(main())
