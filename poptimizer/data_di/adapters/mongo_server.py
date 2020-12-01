"""Запуск сервера MongoDB."""
import asyncio
import logging
import pathlib
from typing import Optional

import aiohttp
import psutil
from motor import motor_asyncio

from poptimizer.data.config import resources

# Путь к MongoDB и dump с данными по дивидендам
MONGO_PATH = pathlib.Path(__file__).parents[3] / "db"
MONGO_DUMP = pathlib.Path(__file__).parents[3] / "dump"

# Ссылки на данные по дивидендам в интернете
DIV_DATA_URL = (
    (
        "dividends.bson",
        "https://github.com/WLM1ke/poptimizer/blob/master/dump/source/dividends.bson?raw=true",
    ),
    (
        "dividends.metadata.json",
        "https://github.com/WLM1ke/poptimizer/blob/master/dump/source/dividends.metadata.json?raw=true",
    ),
)

# База и коллекция с источником данных по дивидендам
SOURCE_DB = "source"
COLLECTION = "dividends"

# ID и ключ документа с информацией о количестве документов с дивидендами
ID = "count"
KEY = "dividends"


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


async def _download_dump(http_session: aiohttp.ClientSession) -> None:
    """Загружает резервную версию дивидендов с GitHub."""
    if not MONGO_DUMP.exists():
        logging.info("Файлы с данными о дивидендах отсутствуют - начинается загрузка")
        path = MONGO_DUMP / SOURCE_DB
        path.mkdir(parents=True)
        for name, url in DIV_DATA_URL:
            async with http_session.get(url) as respond:
                with open(path / name, "wb") as fin:
                    fin.write(await respond.read())
        logging.info("Файлы с данными о дивидендах загружены")


async def _restore_dump(
    client: motor_asyncio.AsyncIOMotorClient,
) -> None:
    """Осуществляет восстановление данных по дивидендам."""
    if SOURCE_DB not in await client.list_database_names():
        logging.info("Начато восстановление данных с дивидендами")
        mongo_restore = ["mongorestore", MONGO_DUMP]
        process = psutil.Popen(mongo_restore)
        status = process.wait()
        logging.info(f"Восстановление данных с дивидендами завершен со статусом {status}")


async def _dump_dividends_db(client: motor_asyncio.AsyncIOMotorClient) -> None:
    """Осуществляет резервное копирование базы данных с дивидендами."""
    collection = client[SOURCE_DB][COLLECTION]
    n_docs = await collection.count_documents({})
    div_count = await collection.find_one({"_id": ID})
    if div_count is None or n_docs != div_count[KEY]:
        logging.info(f"Backup данных с дивидендами {n_docs - 1} документов")
        process = psutil.Popen(["mongodump", "--out", MONGO_DUMP, "--db", SOURCE_DB])
        status = process.wait()
        await collection.replace_one({"_id": ID}, {KEY: n_docs}, upsert=True)
        logging.info(f"Backup данных с дивидендами завершен со статусом {status}")


def prepare_mongo_db_server() -> None:
    """Запускает сервер.

    При необходимости создает коллекцию с исходными данными по дивидендам или сохраняет ее резервную
    копию.
    """
    loop = asyncio.get_event_loop()
    mongo = resources.get_mongo_client()
    http = resources.get_aiohttp_session()

    start_mongo_server()

    loop.run_until_complete(_download_dump(http))
    loop.run_until_complete(_restore_dump(mongo))
    loop.run_until_complete(_dump_dividends_db(mongo))
