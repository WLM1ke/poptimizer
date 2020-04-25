"""Запуск запуск сервера и клиента MongoDB и соединения с интернетом."""
import atexit
import functools
import logging
import subprocess
from typing import Tuple

import psutil
import pymongo
import requests
from requests import adapters

from poptimizer import config

# Максимальный пул соединений по HTTPS и повторных загрузок
HTTPS_MAX_POOL_SIZE = 20
MAX_RETRIES = 3

# База данных и коллекция по умолчанию
DB = "data"
MISC = "misc"

# Ключ в базе, где хранится количество данных по дивидендам
DIV_COUNT = "div_count"

# База и коллекция с источником данных по дивидендам
SOURCE_DB = "source"
COLLECTION = "dividends"

# Ссылки на данные по дивидендам в интернете
DIV_DATA_URL = {
    "dividends.bson": (
        "https://github.com/WLM1ke/poptimizer/blob/master/dump/source/dividends.bson?raw=true"
    ),
    "dividends.metadata.json": (
        "https://github.com/WLM1ke/poptimizer/blob/master/dump/source/dividends.metadata.json?raw=true"
    ),
}


def start_mongo_server() -> psutil.Process:
    """Запуск сервера MongoDB."""
    for process in psutil.process_iter(attrs=["name"]):
        if "mongod" in process.info["name"]:
            # logging.info("Локальный сервер MongoDB уже работает")
            return process
    # logging.info("Запускается локальный сервер MongoDB")
    config.MONGO_PATH.mkdir(parents=True, exist_ok=True)
    mongo_server = [
        "mongod",
        "--dbpath",
        config.MONGO_PATH,
        "--directoryperdb",
        "--bind_ip",
        "localhost",
    ]
    return psutil.Popen(mongo_server, stdout=subprocess.DEVNULL)


def restore_dump(client: pymongo.MongoClient, http_session: requests.Session) -> None:
    """Осуществляет восстановление данных по дивидендам."""
    if not config.MONGO_DUMP.exists():
        logging.info(f"Файлы с данными о дивидендах отсутствуют - начинается загрузка")
        path = config.MONGO_DUMP / SOURCE_DB
        path.mkdir(parents=True)
        for name, url in DIV_DATA_URL.items():
            with http_session.get(url, stream=True) as respond:
                with open(path / name, "wb") as fin:
                    fin.write(respond.content)
        logging.info(f"Файлы с данными о дивидендах загружены")
    if SOURCE_DB not in client.list_database_names():
        logging.info(f"Начато восстановление данных с дивидендами")
        mongo_restore = ["mongorestore", config.MONGO_DUMP]
        process = psutil.Popen(mongo_restore)
        status = process.wait()
        logging.info(
            f"Восстановление данных с дивидендами завершен со статусом {status}"
        )


def start_mongo_client(http_session: requests.Session) -> pymongo.MongoClient:
    """Открытие клиентского соединения с MongoDB."""
    # logging.info("Создается клиент MongoDB")
    client = pymongo.MongoClient("localhost", 27017, tz_aware=False)
    restore_dump(client, http_session)
    return client


def start_http_session() -> requests.Session:
    """Открытие клиентского соединение с  интернетом."""
    # logging.info("Открывается сессия для обновления данных по интернет")
    session = requests.Session()
    adapter = adapters.HTTPAdapter(
        pool_maxsize=HTTPS_MAX_POOL_SIZE, max_retries=MAX_RETRIES, pool_block=True
    )
    session.mount("https://", adapter)
    return session


def dump_dividends_db(client: pymongo.MongoClient) -> None:
    """Осуществляет резервное копирование базы данных с дивидендами."""
    n_docs = client[SOURCE_DB][COLLECTION].count_documents({})
    div_count = client[DB][MISC].find_one({"_id": DIV_COUNT})
    if div_count is None or n_docs != div_count["data"]:
        logging.info(f"Backup данных с дивидендами {n_docs} документов")
        mongo_dump = ["mongodump", "--out", config.MONGO_DUMP, "--db", SOURCE_DB]
        process = psutil.Popen(mongo_dump)
        status = process.wait()
        client[DB][MISC].replace_one({"_id": DIV_COUNT}, {"data": n_docs}, upsert=True)
        logging.info(f"Backup данных с дивидендами завершен со статусом {status}")


def clean_up(client: pymongo.MongoClient, http_session: requests.Session) -> None:
    """Отключение клиента и закрытие соединений."""
    dump_dividends_db(client)

    client.close()
    # logging.info("Подключение клиента MongoDB закрыто")

    http_session.close()
    # logging.info("Сессия для обновления данных по интернет закрыта")


def start_and_setup_clean_up() -> Tuple[
    psutil.Process, pymongo.MongoClient, requests.Session
]:
    """Запуск сервера и клиента MongoDB и соединения с интернетом.

    Регистрация процедуры отключения клиента и закрытия соединения.
    Сервер не отключается.
    """
    server = start_mongo_server()
    http_session = start_http_session()
    client = start_mongo_client(http_session)
    atexit.register(
        functools.partial(clean_up, client=client, http_session=http_session)
    )
    return server, client, http_session


MONGO_PROCESS, MONGO_CLIENT, HTTP_SESSION = start_and_setup_clean_up()
