"""Базовые классы для сохранения доменных объектов в MongoDB."""
import asyncio
import logging
import typing
import weakref
from typing import Callable, ClassVar, MutableMapping, NamedTuple, Optional, Tuple, Type, TypeVar

from motor import motor_asyncio

from poptimizer.data_di.shared import domain

# Коллекция для сохранения объектов из групп с одним объектом
MISC = "misc"


class AsyncLogger:
    """Асинхронное логирование в отдельном потоке.

    Поддерживает протокол дескриптора для автоматического определения имени класса, в котором он
    является атрибутом.
    """

    def __init__(self) -> None:
        """Инициализация логгера."""
        self._logger = logging.getLogger()

    def __set_name__(self, owner: Type[object], name: str) -> None:
        """Создает логгер с именем класса, где он является атрибутом."""
        self._logger = logging.getLogger(owner.__name__)

    def __get__(self, instance: object, owner: Type[object]) -> "AsyncLogger":
        """Возвращает себя при обращении к атрибуту."""
        return self

    def log(self, message: str) -> None:
        """Создает асинхронную задачу по логгированию."""
        asyncio.create_task(self._logging_task(message))

    async def _logging_task(self, message: str) -> None:
        """Задание по логгированию."""
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self._logger.info, message)


class Desc(NamedTuple):
    """Описание кодирования и декодирования из документа MongoDB."""

    field_name: str
    doc_name: str
    factory_name: str
    encoder: Optional[Callable[[typing.Any], typing.Any]] = None  # type: ignore
    decoder: Optional[Callable[[typing.Any], typing.Any]] = None  # type: ignore


def _collection_and_name(table_name: domain.ID) -> Tuple[str, str, str]:
    """Формирует название базы, коллекции и имя документа."""
    collection = table_name.group
    name = table_name.name
    if collection == name:
        collection = MISC
    return table_name.package, collection, name


EntityType = TypeVar("EntityType", bound=domain.BaseEntity)


class Mapper(typing.Generic[EntityType]):
    """Сохраняет и загружает доменные объекты из MongoDB."""

    _identity_map: ClassVar[
        MutableMapping[
            domain.ID,
            EntityType,
        ]
    ] = weakref.WeakValueDictionary()
    _logger: ClassVar[AsyncLogger]

    def __init__(  # type: ignore
        self,
        client: motor_asyncio.AsyncIOMotorClient,
        desc_list: Tuple[Desc, ...],
        factory: domain.AbstractFactory[EntityType],
    ) -> None:
        """Сохраняет соединение с MongoDB."""
        self._client = client
        self._desc_list = desc_list
        self._factory = factory

    async def get(self, id_: domain.ID) -> EntityType:
        """Загружает доменный объект из базы."""
        if (table_old := self._identity_map.get(id_)) is not None:
            return table_old

        table = await self._load_or_create(id_)

        if (table_old := self._identity_map.get(id_)) is not None:
            return table_old

        self._identity_map[id_] = table

        return table

    async def commit(
        self,
        entity: EntityType,
    ) -> None:
        """Записывает изменения доменного объекта в MongoDB."""
        id_ = entity.id_
        self._logger.log(f"Сохранение {id_}")

        db, collection, name = _collection_and_name(id_)

        if mongo_dict := self._encode(entity):
            await self._client[db][collection].replace_one(
                filter={"_id": name},
                replacement=dict(_id=name, **mongo_dict),
                upsert=True,
            )

    async def _load_or_create(self, id_: domain.ID) -> EntityType:
        """Загружает из MongoDB, а в случае отсутствия создается пустой объект."""
        db, collection, name = _collection_and_name(id_)
        db_collection = self._client[db][collection]
        mongo_dict = await db_collection.find_one({"_id": name}, projection={"_id": False})

        if mongo_dict is None:
            mongo_dict = {}

        return self._decode(id_, mongo_dict)

    def _encode(self, entity: EntityType) -> domain.StateDict:
        """Кодирует данные в совместимый с MongoDB формат."""
        if not (entity_state := entity.changed_state()):
            return {}

        entity.clear()
        sentinel = object()
        for desc in self._desc_list:
            if (field_value := entity_state.pop(desc.field_name, sentinel)) is sentinel:
                continue
            if desc.encoder:
                field_value = desc.encoder(field_value)
            entity_state[desc.doc_name] = field_value

        return entity_state

    def _decode(self, id_: domain.ID, mongo_dict: domain.StateDict) -> EntityType:
        """Декодирует данные из формата MongoDB формат атрибутов модели и создает объект."""
        sentinel = object()
        for desc in self._desc_list:
            if (field_value := mongo_dict.pop(desc.field_name, sentinel)) is sentinel:
                continue
            if desc.decoder:
                field_value = desc.decoder(field_value)
            mongo_dict[desc.factory_name] = field_value
        return self._factory(id_, mongo_dict)
