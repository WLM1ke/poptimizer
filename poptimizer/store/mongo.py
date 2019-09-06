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


def start_db() -> Tuple[pymongo.MongoClient, requests.Session]:
    """Запуск сервера и клиента MongoDB и соединения с интернетом."""
    mongo_server = [
        "mongod",
        "--logpath",
        config.MONGO_LOG_PATH,
        "--quiet",
        "--dbpath",
        config.MONGO_PATH,
        "--bind_ip",
        "localhost",
    ]

    logging.info(f"Запускается локальный сервер MongoDB")
    subprocess.Popen(mongo_server, stdout=subprocess.DEVNULL)

    logging.info(f"Подключается клиент MongoDB")
    client = pymongo.MongoClient("localhost", 27017, tz_aware=False)

    logging.info(f"Открывается сессия для обновления данных по интернет")
    session = requests.Session()

    return client, session


@atexit.register
def clean_up() -> None:
    """Отключение сервера и закрытие соединений."""
    admin = CLIENT["admin"]
    try:
        admin.command("shutdown")
    except AutoReconnect:
        logging.info(f"Локальный сервер MongoDB остановлен")
    CLIENT.close()
    logging.info(f"Подключение клиента MongoDB закрыто")
    SESSION.close()
    logging.info(f"Сессия для обновления данных по интернет закрыта")


CLIENT, SESSION = start_db()
