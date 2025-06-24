import ssl
from pathlib import Path
from typing import Final

import aiohttp

_MAX_ISS_CON: Final = 10
_HEADERS: Final = {
    "User-Agent": "POptimizer",
    "Connection": "keep-alive",
}
_CERTS: Final = Path(__file__).parent / "certs"


def client(on_per_host: int = _MAX_ISS_CON) -> aiohttp.ClientSession:
    ctx = ssl.create_default_context()
    ctx.load_verify_locations(capath=_CERTS)
    return aiohttp.ClientSession(
        connector=aiohttp.TCPConnector(
            ssl_context=ctx,
            limit_per_host=on_per_host,
        ),
        headers=_HEADERS,
    )
