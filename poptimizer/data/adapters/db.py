"""Реализации сессий доступа к базе данных."""
import asyncio
from typing import Iterable, Optional, Tuple, Union

import pandas as pd
from motor import motor_asyncio

from poptimizer.data.adapters import logger
from poptimizer.data.ports import outer

# Коллекция для одиночный записей
MISC = "misc"


def _collection_and_name(table_name: Union[outer.TableTuple, outer.TableName]) -> Tuple[str, str]:
    """Формирует название коллекции и имя документа."""
    collection: str = table_name.group
    name = table_name.name
    if collection == name:
        collection = MISC
    return collection, name


class MongoDBSession(outer.AbstractDBSession):
    """Реализация сессии с хранением в MongoDB.

    При совпадении id и группы данные записываются в специальную коллекцию, в ином случае в коллекцию
    группы таблицы.
    """

    def __init__(self, db: motor_asyncio.AsyncIOMotorDatabase) -> None:
        """Получает ссылку на базу данных."""
        self._logger = logger.AsyncLogger(self.__class__.__name__)
        self._db = db

    async def get(self, table_name: outer.TableName) -> Optional[outer.TableTuple]:
        """Извлекает документ из коллекции."""
        collection, name = _collection_and_name(table_name)
        doc = await self._db[collection].find_one({"_id": name})

        if doc is None:
            return None

        df = pd.DataFrame(**doc["data"])
        return outer.TableTuple(*table_name, df=df, timestamp=doc["timestamp"])

    async def commit(self, tables_vars: Iterable[outer.TableTuple]) -> None:
        """Записывает данные в MongoDB."""
        aws = []

        for table in tables_vars:
            collection, name = _collection_and_name(table)
            self._logger.log(f"Сохранение {collection}.{name}")

            aw_update = self._db[collection].replace_one(
                filter={"_id": name},
                replacement=dict(_id=name, data=table.df.to_dict("split"), timestamp=table.timestamp),
                upsert=True,
            )
            aws.append(aw_update)

        await asyncio.gather(*aws)
