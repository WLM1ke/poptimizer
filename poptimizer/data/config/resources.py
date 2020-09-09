"""Конфигурация внешних ресурсов приложения."""
import asyncio
import atexit

import aiohttp
from motor import motor_asyncio

# Пул с асинхронными http-соединениями
AIOHTTP_SESSION = aiohttp.ClientSession()


def get_aiohttp_session() -> aiohttp.ClientSession:
    """Клиентская сессия aiohttp."""
    return AIOHTTP_SESSION


# Настройки MongoDB
_MONGO_URI = "mongodb://localhost:27017"
MONGO_CLIENT = motor_asyncio.AsyncIOMotorClient(_MONGO_URI, tz_aware=False)


def get_mongo_client() -> motor_asyncio.AsyncIOMotorClient:
    """Асинхронный клиент для работы с MongoDB."""
    return MONGO_CLIENT


def clean_up() -> None:
    """Закрывает клиентскую сессию aiohttp."""
    loop = asyncio.get_event_loop()
    loop.run_until_complete(AIOHTTP_SESSION.close())


atexit.register(clean_up)
