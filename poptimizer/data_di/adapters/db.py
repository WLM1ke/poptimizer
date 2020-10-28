"""Реализации сессий доступа к базе данных."""
from typing import Optional, Tuple, Type

from injector import Inject
from motor.motor_asyncio import AsyncIOMotorClient

from poptimizer.data_di.adapters.logger import AsyncLogger
from poptimizer.data_di.adapters.mapper import Mapper
from poptimizer.data_di.ports import tables
from poptimizer.data_di.shared import entity

# Коллекция для одиночный записей
MISC = "misc"


def _collection_and_name(table_name: entity.ID) -> Tuple[str, str, str]:
    """Формирует название базы, коллекции и имя документа."""
    collection = table_name.group
    name = table_name.name
    if collection == name:
        collection = MISC
    return table_name.package, collection, name


class MongoDBSession(tables.AbstractDBSession):
    """Реализация сессии с хранением в MongoDB.

    При совпадении id и группы данные записываются в специальную коллекцию, в ином случае в коллекцию
    группы таблицы.
    """

    def __init__(
        self,
        client: Inject[AsyncIOMotorClient],
        mapper: Inject[Mapper],
        logger_type: Inject[Type[AsyncLogger]],
    ) -> None:
        """Получает ссылку на базу данных."""
        self._logger = logger_type(self.__class__.__name__)
        self._mapper = mapper
        self._client = client

    async def get(self, id_: entity.ID) -> Optional[tables.TableDict]:
        """Извлекает документ из коллекции."""
        db, collection, name = _collection_and_name(id_)
        db_collection = self._client[db][collection]
        doc = await db_collection.find_one({"_id": name}, projection={"_id": False})

        if doc is None:
            return None

        return self._mapper.decode(doc)

    async def commit(self, id_: entity.ID, tables_vars: tables.TableDict) -> None:
        """Записывает данные в MongoDB."""
        self._logger.log(f"Сохранение {id_}")

        db, collection, name = _collection_and_name(id_)
        doc = self._mapper.encode(tables_vars)

        await self._client[db][collection].replace_one(
            filter={"_id": name},
            replacement=dict(_id=name, **doc),
            upsert=True,
        )
