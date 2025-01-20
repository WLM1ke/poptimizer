from typing import Final

import aiohttp

_MAX_ISS_CON: Final = 10
_HEADERS: Final = {
    "User-Agent": "POptimizer",
    "Connection": "keep-alive",
}


def client(on_per_host: int = _MAX_ISS_CON) -> aiohttp.ClientSession:
    return aiohttp.ClientSession(
        connector=aiohttp.TCPConnector(limit_per_host=on_per_host),
        headers=_HEADERS,
    )
