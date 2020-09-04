"""Конфигурация внешних ресурсов приложения."""
from concurrent import futures

import pymongo
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


# Настройки клиента MongoDB
PORT = 27017
CLIENT = pymongo.MongoClient("localhost", PORT, tz_aware=False)


def get_mongo_client() -> pymongo.MongoClient:
    """Клиентское соединение с MongoDB."""
    return CLIENT


# Настройки пула потоков - количество потоков равно размеру пула http-соединений
THREAD_POOL = futures.ThreadPoolExecutor(max_workers=MAX_POOL_SIZE)


def get_thread_pool() -> futures.ThreadPoolExecutor:
    """Пул потоков."""
    return THREAD_POOL
