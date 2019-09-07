"""Запуск и остановка сервера и клиента MongoDB и соединения с интернетом.

Остановка производится автоматически после завершения программы.
"""
import atexit
import functools
import logging
import subprocess

import pymongo
import requests
from pymongo.errors import AutoReconnect

from poptimizer import config


def start_mongo_server() -> subprocess.Popen:
    """Запуск сервера MongoDB."""
    logging.info(f"Запускается локальный сервер MongoDB")
    mongo_server = ["mongod", "--dbpath", config.MONGO_PATH, "--bind_ip", "localhost"]
    return subprocess.Popen(mongo_server, stdout=subprocess.DEVNULL)


def start_mongo_client() -> pymongo.MongoClient:
    """Открытие клиентского соединения с MongoDB."""
    logging.info(f"Подключается клиент MongoDB")
    client = pymongo.MongoClient(
        "localhost", 27017, tz_aware=False, serverSelectionTimeoutMS=1000
    )
    return client


def start_http_session() -> requests.Session:
    """Открытие клиентского соединение с  интернетом."""
    logging.info(f"Открывается сессия для обновления данных по интернет")
    session = requests.Session()
    return session


def clean_up(process: subprocess.Popen) -> None:
    """Отключение сервера и закрытие соединений."""
    admin = DB_CLIENT["admin"]
    try:
        admin.command("shutdown")
    except AutoReconnect:
        pass
    if process.wait() == 0:
        logging.info(f"Локальный сервер MongoDB остановлен")
    DB_CLIENT.close()
    logging.info(f"Подключение клиента MongoDB закрыто")
    HTTP_SESSION.close()
    logging.info(f"Сессия для обновления данных по интернет закрыта")


MONGO_PROCESS = start_mongo_server()
DB_CLIENT = start_mongo_client()
HTTP_SESSION = start_http_session()
atexit.register(functools.partial(clean_up, MONGO_PROCESS))
