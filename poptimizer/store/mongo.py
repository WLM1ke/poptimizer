"""Запуск и остановка сервера и клиента MongoDB и соединения с интернетом.

Остановка производится автоматически после завершения программы.
"""
import atexit
import functools
import logging
import signal
import subprocess

import psutil
import pymongo
import requests
from requests import adapters

from poptimizer import config

# Максимальный пул соединений по HTTPS и повторных загрузок
HTTPS_MAX_POOL_SIZE = 20
MAX_RETRIES = 3


def start_mongo_server() -> psutil.Process:
    """Запуск сервера MongoDB."""
    for process in psutil.process_iter(attrs=["name"]):
        if "mongod" in process.info["name"]:
            logging.info("Локальный сервер MongoDB уже работает")
            return process
    logging.info("Запускается локальный сервер MongoDB")
    mongo_server = [
        "mongod",
        "--dbpath",
        config.MONGO_PATH,
        "--directoryperdb",
        "--bind_ip",
        "localhost",
    ]
    return psutil.Popen(mongo_server, stdout=subprocess.DEVNULL)


def start_mongo_client() -> pymongo.MongoClient:
    """Открытие клиентского соединения с MongoDB."""
    logging.info("Создается клиент MongoDB")
    client = pymongo.MongoClient("localhost", 27017, tz_aware=False)
    return client


def start_http_session() -> requests.Session:
    """Открытие клиентского соединение с  интернетом."""
    logging.info("Открывается сессия для обновления данных по интернет")
    session = requests.Session()
    adapter = adapters.HTTPAdapter(
        pool_maxsize=HTTPS_MAX_POOL_SIZE, max_retries=MAX_RETRIES, pool_block=True
    )
    session.mount("https://", adapter)
    return session


def clean_up(mongo_process: psutil.Process) -> None:
    """Отключение сервера и закрытие соединений."""
    MONGO_CLIENT.close()
    logging.info("Подключение клиента MongoDB закрыто")

    mongo_process.send_signal(signal.SIGTERM)
    status = mongo_process.wait()
    logging.info(f"Локальный сервер MongoDB остановлен со статусом {status}")

    HTTP_SESSION.close()
    logging.info("Сессия для обновления данных по интернет закрыта")


MONGO_PROCESS = start_mongo_server()
MONGO_CLIENT = start_mongo_client()
HTTP_SESSION = start_http_session()
atexit.register(functools.partial(clean_up, MONGO_PROCESS))
