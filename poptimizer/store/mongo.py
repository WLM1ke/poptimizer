"""Запуск и остановка сервера и клиента MongoDB и соединения с интернетом.

Остановка производится автоматически после завершения программы.
"""
import atexit
import functools
import logging
import subprocess

import psutil
import pymongo
import requests
from pymongo.errors import AutoReconnect, ServerSelectionTimeoutError

from poptimizer import config


def start_mongo_client() -> pymongo.MongoClient:
    """Открытие клиентского соединения с MongoDB."""
    logging.info("Создается клиент MongoDB")
    client = pymongo.MongoClient(
        "localhost", 27017, tz_aware=False, serverSelectionTimeoutMS=1000
    )
    return client


def start_mongo_server(test_client: pymongo.MongoClient) -> psutil.Process:
    """Запуск сервера MongoDB."""
    try:
        pid = test_client["admin"].command("serverStatus")["pid"]
    except ServerSelectionTimeoutError:
        logging.info("Запускается локальный сервер MongoDB")
        mongo_server = [
            "mongod",
            "--dbpath",
            config.MONGO_PATH,
            "--bind_ip",
            "localhost",
        ]
        return psutil.Popen(mongo_server, stdout=subprocess.DEVNULL)
    else:
        logging.info("Локальный сервер MongoDB уже работает")
        return psutil.Process(pid)


def start_http_session() -> requests.Session:
    """Открытие клиентского соединение с  интернетом."""
    logging.info("Открывается сессия для обновления данных по интернет")
    session = requests.Session()
    return session


def clean_up(mongo_process: psutil.Process) -> None:
    """Отключение сервера и закрытие соединений."""
    admin = DB_CLIENT["admin"]
    try:
        admin.command("shutdown")
    except AutoReconnect:
        pass
    status = mongo_process.wait()
    logging.info(f"Локальный сервер MongoDB остановлен со статусом {status}")
    DB_CLIENT.close()
    logging.info("Подключение клиента MongoDB закрыто")
    HTTP_SESSION.close()
    logging.info("Сессия для обновления данных по интернет закрыта")


DB_CLIENT = start_mongo_client()
MONGO_PROCESS = start_mongo_server(DB_CLIENT)
HTTP_SESSION = start_http_session()
atexit.register(functools.partial(clean_up, MONGO_PROCESS))
