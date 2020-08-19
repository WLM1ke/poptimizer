"""Реализации сессий доступа к базе данных."""
from typing import Iterable, Optional, Tuple

import pandas as pd
import pymongo

from poptimizer.data.core import ports

# База данных, база для одиночный значений и соединение
DB = "data_new"
MISC = "misc"
PORT = 27017
CLIENT = pymongo.MongoClient("localhost", PORT, tz_aware=False)


def get_mongo_client() -> pymongo.MongoClient:
    """Клиентское соединение с MongoDB."""
    return CLIENT


class MongoDBSession(ports.AbstractDBSession):
    """Реализация сессии с хранением в MongoDB.

    При совпадении id и группы данные записываются в специальную коллекцию, в ином случае в коллекцию
    группы.
    """

    def __init__(self) -> None:
        """Получает ссылку на базу данных."""
        client = get_mongo_client()
        self._db = client[DB]

    def get(self, name: Tuple[str, str]) -> Optional[ports.TableVars]:
        """Извлекает документ из коллекции."""
        group, id_ = name
        collection = group
        if collection == id_:
            collection = MISC
        if (doc := self._db[collection].find_one({"_id": id_})) is None:
            return None
        df = pd.DataFrame(**doc["data"])
        return ports.TableVars(group=group, id_=id_, df=df, timestamp=doc["timestamp"])

    def commit(self, tables_vars: Iterable[ports.TableVars]) -> None:
        """Записывает данные в MongoDB."""
        for table in tables_vars:
            collection = table.group
            id_ = table.id_
            if collection == table.id_:
                collection = MISC
            doc = dict(_id=id_, data=table.df.to_dict("split"), timestamp=table.timestamp)
            self._db[collection].replace_one({"_id": id_}, doc, upsert=True)


class InMemoryDBSession(ports.AbstractDBSession):
    """Реализация сессии с хранением в памяти для тестов."""

    def __init__(self, tables_vars: Optional[Iterable[ports.TableVars]] = None) -> None:
        """Создает хранилище в памяти."""
        self.committed = {}
        if tables_vars is not None:
            self.committed.update(
                {(table_vars.group, table_vars.id_): table_vars for table_vars in tables_vars},
            )

    def get(self, name: Tuple[str, str]) -> Optional[ports.TableVars]:
        """Выдает таблицы, переданные при создании."""
        return self.committed.get(name)

    def commit(self, tables_vars: Iterable[ports.TableVars]) -> None:
        """Дополняет словарь таблиц, переданных при создании."""
        tables_dict = {(table_vars.group, table_vars.id_): table_vars for table_vars in tables_vars}
        return self.committed.update(tables_dict)
