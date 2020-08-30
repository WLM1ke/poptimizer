"""Реализации сессий доступа к базе данных."""
import logging
from typing import Iterable, Optional

import pandas as pd
import pymongo

from poptimizer.data.ports import base, outer

# База данных, база для одиночный значений и соединение
DB = "data_new"
MISC = "misc"
PORT = 27017
CLIENT = pymongo.MongoClient("localhost", PORT, tz_aware=False)


logger = logging.getLogger("MongoDB")


def get_mongo_client() -> pymongo.MongoClient:
    """Клиентское соединение с MongoDB."""
    return CLIENT


class MongoDBSession(outer.AbstractDBSession):
    """Реализация сессии с хранением в MongoDB.

    При совпадении id и группы данные записываются в специальную коллекцию, в ином случае в коллекцию
    группы.
    """

    def __init__(self) -> None:
        """Получает ссылку на базу данных."""
        client = get_mongo_client()
        self._db = client[DB]

    def get(self, table_name: base.TableName) -> Optional[base.TableTuple]:
        """Извлекает документ из коллекции."""
        group, name = table_name
        collection: str = group
        if collection == name:
            collection = MISC
        if (doc := self._db[collection].find_one({"_id": name})) is None:
            return None
        df = pd.DataFrame(**doc["data"])
        return base.TableTuple(group=group, name=name, df=df, timestamp=doc["timestamp"])

    def commit(self, tables_vars: Iterable[base.TableTuple]) -> None:
        """Записывает данные в MongoDB."""
        for table in tables_vars:
            collection: str = table.group
            name = table.name
            if collection == name:
                collection = MISC
            logger.info(f"Сохраняю {collection}.{name}")
            doc = dict(_id=name, data=table.df.to_dict("split"), timestamp=table.timestamp)
            self._db[collection].replace_one({"_id": name}, doc, upsert=True)


class InMemoryDBSession(outer.AbstractDBSession):
    """Реализация сессии с хранением в памяти для тестов."""

    def __init__(self, tables_vars: Optional[Iterable[base.TableTuple]] = None) -> None:
        """Создает хранилище в памяти."""
        self.committed = {}
        if tables_vars is not None:
            self.committed.update(
                {(table_vars.group, table_vars.name): table_vars for table_vars in tables_vars},
            )

    def get(self, table_name: base.TableName) -> Optional[base.TableTuple]:
        """Выдает таблицы, переданные при создании."""
        return self.committed.get(table_name)

    def commit(self, tables_vars: Iterable[base.TableTuple]) -> None:
        """Дополняет словарь таблиц, переданных при создании."""
        tables_dict = {(table_vars.group, table_vars.name): table_vars for table_vars in tables_vars}
        return self.committed.update(tables_dict)
