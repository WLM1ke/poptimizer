import ssl
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Final

import aiohttp
from pydantic import ValidationError

from poptimizer.core import errors

_MAX_ISS_CON: Final = 10
_HEADERS: Final = {
    "User-Agent": "POptimizer",
    "Connection": "keep-alive",
}
_CERTS: Final = Path(__file__).parent / "certs" / "all_certs.pem"


def client(on_per_host: int = _MAX_ISS_CON) -> aiohttp.ClientSession:
    ctx = ssl.create_default_context()
    ctx.load_verify_locations(cafile=_CERTS)
    return aiohttp.ClientSession(
        connector=aiohttp.TCPConnector(
            ssl_context=ctx,
            limit_per_host=on_per_host,
        ),
        headers=_HEADERS,
    )


@asynccontextmanager
async def wrap_err(msg: str) -> AsyncGenerator[None]:
    try:
        yield
    except (TimeoutError, aiohttp.ClientError, ValidationError) as err:
        raise errors.AdapterError(msg) from err
