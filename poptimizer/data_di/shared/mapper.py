"""Базовые классы для сохранения доменных объектов в MongoDB."""
from typing import Callable, NamedTuple, Optional, Tuple, Type

from motor.motor_asyncio import AsyncIOMotorClient

import poptimizer.data_di
from poptimizer.data_di.shared import entity
from poptimizer.data_di.shared.logger import AsyncLogger

# Коллекция для сохранения объектов из групп с одним объектом
MISC = "misc"


class Desc(NamedTuple):
    """Описание кодирования и декодирования из документа MongoDB."""

    field_name: str
    doc_name: str
    factory_name: str
    encoder: Optional[Callable] = None  # type: ignore
    decoder: Optional[Callable] = None  # type: ignore


class Mapper:
    """Преобразует данные словаря состояния в документ MongoDB и аргументы фабричного метода объекта."""

    def __init__(self, desc_list: Tuple[Desc, ...]) -> None:
        """Сохраняет описание кодировки."""
        self._to_doc = {desc.field_name: desc for desc in desc_list}
        self._from_doc = {desc.doc_name: desc for desc in desc_list}

    def encode(self, attr_dict: entity.StateDict) -> entity.StateDict:
        """Кодирует данные в совместимый с MongoDB формат."""
        desc_dict = self._to_doc
        mongo_dict = {}
        for name, attr_value in attr_dict.items():
            desc = desc_dict[name]
            if desc.encoder:
                attr_value = desc.encoder(attr_value)
            mongo_dict[desc.doc_name] = attr_value
        return mongo_dict

    def decode(self, mongo_dict: entity.StateDict) -> entity.StateDict:
        """Декодирует данные из формата MongoDB формат атрибутов модели."""
        desc_dict = self._from_doc
        attr_dict = {}
        for name, attr_value in mongo_dict.items():
            desc = desc_dict[name]
            if desc.decoder:
                attr_value = desc.decoder(attr_value)
            attr_dict[desc.factory_name] = attr_value
        return attr_dict


def _collection_and_name(table_name: entity.ID) -> Tuple[str, str, str]:
    """Формирует название базы, коллекции и имя документа."""
    collection = table_name.group
    name = table_name.name
    if collection == name:
        collection = MISC
    return table_name.package, collection, name


class MongoDBSession:
    """Реализация сессии с хранением в MongoDB.

    При совпадении id и группы данные записываются в специальную коллекцию.
    """

    def __init__(
        self,
        client: AsyncIOMotorClient,
        mapper: Mapper,
        logger_type: Type[AsyncLogger],
    ) -> None:
        """Получает ссылку на базу данных."""
        self._logger = logger_type(self.__class__.__name__)
        self._mapper = mapper
        self._client = client

    async def get(self, id_: entity.ID) -> Optional[poptimizer.data_di.shared.entity.StateDict]:
        """Извлекает документ из коллекции."""
        db, collection, name = _collection_and_name(id_)
        db_collection = self._client[db][collection]
        doc = await db_collection.find_one({"_id": name}, projection={"_id": False})

        if doc is None:
            return None

        return self._mapper.decode(doc)

    async def commit(
        self,
        id_: entity.ID,
        tables_vars: poptimizer.data_di.shared.entity.StateDict,
    ) -> None:
        """Записывает данные в MongoDB."""
        self._logger.log(f"Сохранение {id_}")

        db, collection, name = _collection_and_name(id_)
        doc = self._mapper.encode(tables_vars)

        await self._client[db][collection].replace_one(
            filter={"_id": name},
            replacement=dict(_id=name, **doc),
            upsert=True,
        )
