"""Unit of Work and EventBus."""
import asyncio
import typing
from types import TracebackType
from typing import AsyncContextManager, Callable, Generic, List, Optional, Set, Type, TypeVar

from poptimizer.data_di.shared import adapters, domain

EntityType = TypeVar("EntityType", bound=domain.BaseEntity)


class UoW(AsyncContextManager[domain.AbstractRepo[EntityType]], domain.AbstractRepo[EntityType]):
    """Контекстный менеджер транзакции.

    Предоставляет интерфейс репо, хранит загруженные доменные объекты и сохраняет их при выходе из
    контекста.
    """

    def __init__(self, mapper: adapters.Mapper[EntityType]) -> None:
        """Сохраняет mapper и является его тонкой надстройкой."""
        self._mapper = mapper
        self._seen: Set[EntityType] = set()

    async def __aenter__(self) -> domain.AbstractRepo[EntityType]:
        """Возвращает репо с таблицами."""
        return self

    async def get(self, id_: domain.ID) -> EntityType:
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


if typing.TYPE_CHECKING:
    FutureEvent = asyncio.Future[List[domain.AbstractEvent]]
else:
    FutureEvent = asyncio.Future
PendingTasks = Set[FutureEvent]


class EventBus(Generic[EntityType]):
    """Шина для обработки событий."""

    _logger = adapters.AsyncLogger()

    def __init__(
        self,
        uow_factory: Callable[[], UoW[EntityType]],
        event_handler: domain.AbstractHandler[EntityType],
    ):
        """Для работы нужна фабрика транзакций и обработчик событий."""
        self._uow_factory = uow_factory
        self._event_handler = event_handler

    def handle_event(
        self,
        event: domain.AbstractEvent,
    ) -> None:
        """Обработка сообщения."""
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self._handle_event(event))

    async def _handle_event(
        self,
        event: domain.AbstractEvent,
    ) -> None:
        """Асинхронная обработка сообщения и следующих за ним."""
        pending: PendingTasks = self._create_tasks([event])
        while pending:
            done, pending = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED)

            for task in done:
                pending |= self._create_tasks(task.result())

    def _create_tasks(self, events: List[domain.AbstractEvent]) -> Set[FutureEvent]:
        """Создает задание для событий."""
        return {asyncio.create_task(self._handle_one_command(event)) for event in events}

    async def _handle_one_command(self, event: domain.AbstractEvent) -> List[domain.AbstractEvent]:
        """Обрабатывает одно событие и помечает его сделанным."""
        self._logger(str(event))

        async with self._uow_factory() as repo:
            return await self._event_handler.handle_event(event, repo)
