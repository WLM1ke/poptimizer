"""Общие соединения http и MongoDB."""
import asyncio
import atexit
import pathlib
from typing import Final, Optional

import aiohttp
import psutil
from motor import motor_asyncio

# Настройки сервера MongoDB
_MONGO_PATH: Final = pathlib.Path(__file__).parents[3] / "db"
_MONGO_URI: Final = "mongodb://localhost:27017"

# Размер пула http-соединений - при большем размере многие сайты ругаются
_POOL_SIZE: Final = 20


def _find_running_mongo_db() -> Optional[psutil.Process]:
    """Проверяет наличие запущенной MongoDB и возвращает ее процесс."""
    for process in psutil.process_iter(attrs=["name"]):
        if process.name() == "mongod":
            return process
    return None


def start_mongo_server() -> psutil.Process:
    """Запуск сервера MongoDB."""
    if process := _find_running_mongo_db():
        return process

    _MONGO_PATH.mkdir(parents=True, exist_ok=True)
    mongo_server = [
        "mongod",
        "--dbpath",
        _MONGO_PATH,
        "--directoryperdb",
        "--bind_ip",
        "localhost",
    ]
    return psutil.Popen(mongo_server)


def _clean_up(session: aiohttp.ClientSession) -> None:
    """Закрывает клиентскую сессию aiohttp."""
    loop = asyncio.get_event_loop()
    loop.run_until_complete(session.close())


def http_session_factory(pool_size: int) -> aiohttp.ClientSession:
    """Клиентская сессия aiohttp."""
    connector = aiohttp.TCPConnector(limit=pool_size)
    session = aiohttp.ClientSession(connector=connector)
    atexit.register(_clean_up, session)
    return session


start_mongo_server()
MONGO_CLIENT: Final = motor_asyncio.AsyncIOMotorClient(_MONGO_URI, tz_aware=False)
HTTP_SESSION: Final = http_session_factory(_POOL_SIZE)
