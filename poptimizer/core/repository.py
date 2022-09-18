"""Реализация репозитория для доменных объектов."""
from typing import Any, AsyncIterator, Final, TypeVar

from motor.motor_asyncio import AsyncIOMotorClient

from poptimizer.core import domain

_MONGO_ID: Final = "_id"

Entity = TypeVar("Entity", bound=domain.BaseEntity)


class Repo:
    """Репозиторий для хранения доменных объектов.

    При сохранении валидирует данные.
    """

    def __init__(self, client: AsyncIOMotorClient) -> None:
        self._client = client

    async def get(self, entity_type: type[Entity], id_: str | None = None) -> Entity:
        """Загружает доменную сущность."""
        collection = self._client[entity_type.group.module][entity_type.group.group]
        id_ = id_ or entity_type.group.group

        doc = await collection.find_one({_MONGO_ID: id_})

        return entity_type.parse_obj(doc or {_MONGO_ID: id_})

    async def save(self, entity: Entity[Entity_co]) -> None:
        """Валидирует и сохраняет доменную сущность."""
        doc = _validate(entity)

        collection = self._client[entity.group.module][entity.group.group]

        await collection.replace_one(
            filter={_MONGO_ID: entity.id_},
            replacement=doc,
            upsert=True,
        )


def _validate(table: Entity) -> dict[str, Any]:
    doc = table.dict()

    table.parse_obj(doc | {_MONGO_ID: table.id_})

    return doc
