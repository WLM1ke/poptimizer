"""Unit of Work и Repo."""
import abc
import asyncio
from types import TracebackType
from typing import AsyncContextManager, Generic, Optional, Set, Type, TypeVar, cast

from poptimizer.data_di.shared import entities, mappers

EntityType = TypeVar("EntityType", bound=entities.BaseEntity)


class AbstractRepo(Generic[EntityType], abc.ABC):
    """Абстрактный класс репозитория."""

    async def get(self, id_: entities.ID) -> Optional[EntityType]:
        """Получить доменный объект по ID."""


class UoW(AsyncContextManager[AbstractRepo[EntityType]]):
    """Контекстный менеджер транзакции.

    Предоставляет интерфейс репо, хранит загруженные доменные объекты и сохраняет их при выходе из
    контекста.
    """

    def __init__(self, mapper: mappers.Mapper[EntityType]) -> None:
        """Сохраняет mapper и является его тонкой надстройкой."""
        self._mapper = mapper
        self._seen: Set[EntityType] = set()

    async def __aenter__(self) -> AbstractRepo[EntityType]:
        """Возвращает репо с таблицами."""
        return cast(AbstractRepo[EntityType], self)

    async def get(self, id_: entities.ID) -> Optional[EntityType]:
        """Загружает доменный объект из базы."""
        entity = await self._mapper.get(id_)
        self._seen.add(entity)
        return entity

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_value: Optional[BaseException],
        traceback: Optional[TracebackType],
    ) -> None:
        """Сохраняет изменные доменные объекты в MongoDB."""
        commit = self._mapper.commit
        await asyncio.gather(*[commit(entity) for entity in self._seen])
