"""Конфигурация внешних ресурсов приложения."""
import asyncio
import atexit

import aiohttp
import requests
from requests import adapters

# Настройки http-соединения
MAX_POOL_SIZE = 20
MAX_RETRIES = 3


def start_http_session() -> requests.Session:
    """Открытие пула соединений с интернетом."""
    session = requests.Session()
    adapter = adapters.HTTPAdapter(pool_maxsize=MAX_POOL_SIZE, max_retries=MAX_RETRIES, pool_block=True)
    session.mount("https://", adapter)
    return session


HTTP_SESSION = start_http_session()


def get_http_session() -> requests.Session:
    """Сессия  http-соединений."""
    return HTTP_SESSION


AIOHTTP_SESSION = aiohttp.ClientSession()


def get_aiohttp_session() -> aiohttp.ClientSession:
    """Клиентская сессия aiohttp."""
    return AIOHTTP_SESSION


def clean_up() -> None:
    """Закрывает клиентскую сессию aiohttp."""
    loop = asyncio.get_event_loop()
    loop.run_until_complete(AIOHTTP_SESSION.close())


atexit.register(clean_up)
