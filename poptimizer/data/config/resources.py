"""Конфигурация общих внешних ресурсов приложения."""
import asyncio
import atexit
from typing import Final

import aiohttp
from motor import motor_asyncio

# Пул с асинхронными http-соединениями
_POOL_SIZE = 20
_CONN = aiohttp.TCPConnector(limit=_POOL_SIZE)
AIOHTTP_SESSION: Final = aiohttp.ClientSession(connector=_CONN)

# Асинхронный клиент для MongoDB
_MONGO_URI = "mongodb://localhost:27017"
MONGO_CLIENT: Final = motor_asyncio.AsyncIOMotorClient(_MONGO_URI, tz_aware=False)


def get_aiohttp_session() -> aiohttp.ClientSession:
    """Клиентская сессия aiohttp."""
    return AIOHTTP_SESSION


def get_mongo_client() -> motor_asyncio.AsyncIOMotorClient:
    """Асинхронный клиент для работы с MongoDB."""
    return MONGO_CLIENT


def _clean_up() -> None:
    """Закрывает клиентскую сессию aiohttp."""
    loop = asyncio.get_event_loop()
    loop.run_until_complete(AIOHTTP_SESSION.close())


atexit.register(_clean_up)
