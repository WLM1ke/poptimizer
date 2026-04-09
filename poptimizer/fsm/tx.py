import asyncio
import logging
from collections.abc import AsyncIterator
from types import TracebackType
from typing import Any, Self

from poptimizer.core import domain, fsm
from poptimizer.evolve.evolution import evolve
from poptimizer.fsm import uow


class Dispatcher:
    def __init__(self) -> None:
        self._inboxes = list[asyncio.Queue[fsm.Event]()]()

    def new_inbox(self) -> asyncio.Queue[fsm.Event]:
        self._inboxes.append(asyncio.Queue[fsm.Event]())

        return self._inboxes[-1]

    def send(self, event: fsm.Event) -> None:
        for inbox in self._inboxes:
            inbox.put_nowait(event)


class Tx:
    def __init__(
        self,
        lgr: logging.Logger,
        repo: uow.Repo,
        dispatcher: Dispatcher,
    ) -> None:
        self._lgr = lgr
        self._repo = repo
        self._dispatcher = dispatcher

        self._uow = uow.UOW(repo)
        self._events: list[fsm.Event] = []

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if exc_type is None:
            await self._uow.save()

            for event in self._events:
                self._dispatcher.send(event)
                self._lgr.info(f"Sending {event}")

    def info(self, msg: str, *args: Any) -> None:
        self._lgr.info(msg, *args)

    def warning(self, msg: str, *args: Any) -> None:
        self._lgr.warning(msg, *args)

    def send(self, event: fsm.Event) -> None:
        self._events.append(event)

    async def get[E: domain.Object](
        self,
        t_entity: type[E],
        uid: domain.UID | None = None,
    ) -> E:
        return await self._uow.get(t_entity, uid)

    async def get_for_update[E: domain.Object](
        self,
        t_entity: type[E],
        uid: domain.UID | None = None,
    ) -> E:
        return await self._uow.get_for_update(t_entity, uid)

    async def delete(self, entity: domain.Object) -> None:
        await self._uow.delete(entity)

    async def count_models(self) -> int:
        return await self._uow.count_models()

    async def next_model_for_update(self) -> evolve.Model:
        return await self._uow.next_model_for_update()

    async def delete_worst_model(self) -> None:
        await self._uow.delete_worst_model()

    async def get_models(self, day: domain.Day) -> list[evolve.Model]:
        return await self._uow.get_models(day)

    async def sample_models(self, n: int) -> list[evolve.Model]:
        return await self._uow.sample_models(n)

    def get_all[E: domain.Object](
        self,
        t_entity: type[E],
    ) -> AsyncIterator[E]:
        return self._uow.get_all(t_entity)

    async def drop(self, entity_type: type[domain.Object]) -> None:
        await self._uow.drop(entity_type)
