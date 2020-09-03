"""Реализации сессий доступа к базе данных."""
import logging
from typing import Iterable, Optional

import pandas as pd

from poptimizer.data.config.resources import get_mongo_client
from poptimizer.data.ports import base, outer

# База данных и коллекция для одиночный
DB = "data_new"
MISC = "misc"


class MongoDBSession(outer.AbstractDBSession):
    """Реализация сессии с хранением в MongoDB.

    При совпадении id и группы данные записываются в специальную коллекцию, в ином случае в коллекцию
    группы.
    """

    def __init__(self) -> None:
        """Получает ссылку на базу данных."""
        self._logger = logging.getLogger(self.__class__.__name__)
        client = get_mongo_client()
        self._db = client[DB]

    def get(self, table_name: base.TableName) -> Optional[outer.TableTuple]:
        """Извлекает документ из коллекции."""
        group, name = table_name
        collection: str = group
        if collection == name:
            collection = MISC
        if (doc := self._db[collection].find_one({"_id": name})) is None:
            return None
        df = pd.DataFrame(**doc["data"])
        return outer.TableTuple(group=group, name=name, df=df, timestamp=doc["timestamp"])

    def commit(self, tables_vars: Iterable[outer.TableTuple]) -> None:
        """Записывает данные в MongoDB."""
        logger = self._logger
        for table in tables_vars:
            collection: str = table.group
            name = table.name
            if collection == name:
                collection = MISC
            logger.info(f"Сохранение {collection}.{name}")
            doc = dict(_id=name, data=table.df.to_dict("split"), timestamp=table.timestamp)
            self._db[collection].replace_one({"_id": name}, doc, upsert=True)


class InMemoryDBSession(outer.AbstractDBSession):
    """Реализация сессии с хранением в памяти для тестов."""

    def __init__(self, tables_vars: Optional[Iterable[outer.TableTuple]] = None) -> None:
        """Создает хранилище в памяти."""
        self.committed = {}
        if tables_vars is not None:
            self.committed.update(
                {(table_vars.group, table_vars.name): table_vars for table_vars in tables_vars},
            )

    def get(self, table_name: base.TableName) -> Optional[outer.TableTuple]:
        """Выдает таблицы, переданные при создании."""
        return self.committed.get(table_name)

    def commit(self, tables_vars: Iterable[outer.TableTuple]) -> None:
        """Дополняет словарь таблиц, переданных при создании."""
        tables_dict = {(table_vars.group, table_vars.name): table_vars for table_vars in tables_vars}
        return self.committed.update(tables_dict)
