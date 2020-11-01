"""Базовые классы для сохранения доменных объектов в MongoDB."""
import abc
import weakref
from typing import Callable, ClassVar, Generic, MutableMapping, NamedTuple, Optional, Tuple, TypeVar

from motor.motor_asyncio import AsyncIOMotorClient

from poptimizer.data_di.shared import aiologger, entities

# Коллекция для сохранения объектов из групп с одним объектом
MISC = "misc"

FieldType = TypeVar("FieldType")
DocType = TypeVar("DocType")


class Desc(Generic[FieldType, DocType], NamedTuple):
    """Описание кодирования и декодирования из документа MongoDB."""

    field_name: str
    doc_name: str
    factory_name: str
    encoder: Optional[Callable[[FieldType], DocType]] = None
    decoder: Optional[Callable[[DocType], FieldType]] = None


def _collection_and_name(table_name: entities.ID) -> Tuple[str, str, str]:
    """Формирует название базы, коллекции и имя документа."""
    collection = table_name.group
    name = table_name.name
    if collection == name:
        collection = MISC
    return table_name.package, collection, name


EntityType = TypeVar("EntityType", bound=entities.BaseEntity)


class Mapper(Generic[EntityType], abc.ABC):
    """Преобразует данные словаря состояния в документ MongoDB и аргументы фабричного метода объекта."""

    logger: aiologger.AsyncLogger["Mapper[EntityType]"]
    desc_list: ClassVar[Tuple[Desc, ...]]
    _identity_map: MutableMapping[
        entities.ID,
        EntityType,
    ] = weakref.WeakValueDictionary()

    def __init__(self, client: AsyncIOMotorClient) -> None:
        """Создает словари для кодирования и декодирования."""
        self._client = client

    async def get(self, id_: entities.ID) -> Optional[EntityType]:
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
        """Записывает данные в MongoDB."""
        id_ = entity.id_
        self.logger.log(f"Сохранение {id_}")

        db, collection, name = _collection_and_name(id_)
        mongo_dict = self._encode(entity)

        await self._client[db][collection].replace_one(
            filter={"_id": name},
            replacement=dict(_id=name, **mongo_dict),
            upsert=True,
        )

    async def _load_or_create(self, id_: entities.ID) -> EntityType:
        """Загружает из базы, а в случае отсутствия создается пустая таблица."""
        db, collection, name = _collection_and_name(id_)
        db_collection = self._client[db][collection]
        mongo_dict = await db_collection.find_one({"_id": name}, projection={"_id": False})

        if mongo_dict is None:
            mongo_dict = {}

        return self._decode(id_, mongo_dict)

    def _encode(self, entity: EntityType) -> entities.StateDict:
        """Кодирует данные в совместимый с MongoDB формат."""
        if entity_state := entity.changed_state():
            entity.clear()

        sentinel = object()
        for desc in self.desc_list:
            if (field_value := entity_state.pop(desc.field_name, sentinel)) is sentinel:
                continue
            if desc.encoder:
                field_value = desc.encoder(field_value)
            entity_state[desc.doc_name] = field_value

        return entity_state

    def _decode(self, id_: entities.ID, mongo_dict: entities.StateDict) -> EntityType:
        """Декодирует данные из формата MongoDB формат атрибутов модели."""
        for desc in self.desc_list:
            field_value = mongo_dict.pop(desc.doc_name)
            if desc.decoder:
                field_value = desc.decoder(field_value)
            mongo_dict[desc.factory_name] = field_value
        return self._factory(id_, mongo_dict)

    @abc.abstractmethod
    def _factory(self, id_: entities.ID, sate_dict: entities.StateDict) -> EntityType:
        """Создает объекты сущности."""
