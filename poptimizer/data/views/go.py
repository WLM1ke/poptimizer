"""Предварительная версия интеграции с Go."""
import aiohttp
from bson import json_util

from poptimizer.shared import connections


async def rest_reader(session: aiohttp.ClientSession = connections.HTTP_SESSION):
    async with session.get("http://localhost:3000/trading_dates/trading_dates") as respond:
        respond.raise_for_status()
        json = await respond.text()

        return json_util.loads(json)


if __name__ == "__main__":
    import asyncio

    loop = asyncio.get_event_loop()
    print(loop.run_until_complete(rest_reader()))
