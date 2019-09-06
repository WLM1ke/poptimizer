"""Запуск и остановка сервера и клиента MongoDB и соединения с интернетом.

Остановка производится автоматически после завершения программы.
"""
import atexit
import logging
import subprocess
from typing import Tuple

import pymongo
import requests
from pymongo.errors import AutoReconnect

from poptimizer import config


def start_mongo() -> None:
    """Запуск сервера MongoDB."""
    mongo_server = ["mongod", "--dbpath", config.MONGO_PATH, "--bind_ip", "localhost"]

    logging.info(f"Запускается локальный сервер MongoDB")
    subprocess.Popen(mongo_server, stdout=subprocess.DEVNULL)


def open_sessions() -> Tuple[pymongo.MongoClient, requests.Session]:
    """Открытие клиентского соединения с MongoDB и интернетом."""
    logging.info(f"Подключается клиент MongoDB")
    client = pymongo.MongoClient(
        "localhost", 27017, tz_aware=False, serverSelectionTimeoutMS=1000
    )

    logging.info(f"Открывается сессия для обновления данных по интернет")
    session = requests.Session()

    return client, session


@atexit.register
def clean_up() -> None:
    """Отключение сервера и закрытие соединений."""
    admin = DB_CLIENT["admin"]
    try:
        admin.command("shutdown")
    except AutoReconnect:
        logging.info(f"Локальный сервер MongoDB остановлен")
    DB_CLIENT.close()
    logging.info(f"Подключение клиента MongoDB закрыто")
    HTTP_SESSION.close()
    logging.info(f"Сессия для обновления данных по интернет закрыта")


start_mongo()
DB_CLIENT, HTTP_SESSION = open_sessions()
