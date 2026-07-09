import asyncio

import httpx


async def test_proxy():
    url = "http://127.0.0.1:8000/api/proxy/mapbox?url=https%3A%2F%2Fapi.mapbox.com%2Fstyles%2Fv1%2Fmapbox%2Fdark-v11%3Fsdk%3Djs-3.3.0"
    async with httpx.AsyncClient() as client:
        r = await client.get(url)
        print("Status:", r.status_code)
        print("Headers:", r.headers)
        print("Content length:", len(r.content))
        if (
            r.status_code == 200
            and r.headers.get("content-type") == "application/json; charset=utf-8"
        ):
            print("Content start:", r.content[:200])
        else:
            print("Response:", r.text[:200])


asyncio.run(test_proxy())
