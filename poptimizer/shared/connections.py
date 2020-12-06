"""Общие соединения http и MongoDB."""
import asyncio
import atexit
import typing
from typing import Final

import aiohttp
from motor import motor_asyncio

# Асинхронный клиент для MongoDB
_MONGO_URI = "mongodb://localhost:27017"
MONGO_CLIENT: typing.Final = motor_asyncio.AsyncIOMotorClient(_MONGO_URI, tz_aware=False)

# Размер пула http-соединений - при большем размере многие сайты ругаются
_POOL_SIZE = 20


def _clean_up(session: aiohttp.ClientSession) -> None:
    """Закрывает клиентскую сессию aiohttp."""
    loop = asyncio.get_event_loop()
    loop.run_until_complete(session.close())


def _session_factory(pool_size: int) -> aiohttp.ClientSession:
    """Клиентская сессия aiohttp."""
    connector = aiohttp.TCPConnector(limit=pool_size)
    session = aiohttp.ClientSession(connector=connector)
    atexit.register(_clean_up, session)
    return session


HTTP_SESSION: Final = _session_factory(_POOL_SIZE)
