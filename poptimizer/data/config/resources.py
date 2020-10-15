"""Конфигурация общих внешних ресурсов приложения."""
import asyncio
import atexit
import pathlib
from typing import Final

import aiohttp
import psutil
from motor import motor_asyncio

# Путь к MongoDB
MONGO_PATH = pathlib.Path(__file__).parents[3] / "db"

# Пул с асинхронными http-соединениями
_POOL_SIZE = 20
_CONN = aiohttp.TCPConnector(limit=_POOL_SIZE)
AIOHTTP_SESSION: Final = aiohttp.ClientSession(connector=_CONN)

# Асинхронный клиент для MongoDB
_MONGO_URI = "mongodb://localhost:27017"
MONGO_CLIENT: Final = motor_asyncio.AsyncIOMotorClient(_MONGO_URI, tz_aware=False)


def start_mongo_server() -> psutil.Process:
    """Запуск сервера MongoDB."""
    for process in psutil.process_iter(attrs=["name"]):
        if "mongod" in process.info["name"]:
            return process
    MONGO_PATH.mkdir(parents=True, exist_ok=True)
    mongo_server = [
        "mongod",
        "--dbpath",
        MONGO_PATH,
        "--directoryperdb",
        "--bind_ip",
        "localhost",
    ]
    return psutil.Popen(mongo_server)


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


start_mongo_server()
atexit.register(_clean_up)
