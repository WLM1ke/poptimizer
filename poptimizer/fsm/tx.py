import asyncio
import logging
from collections.abc import AsyncIterator
from types import TracebackType
from typing import Any, Self

from poptimizer.core import domain, errors, fsm
from poptimizer.evolve.models import evolve
from poptimizer.runtime import uow


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
        store: uow.Store,
        dispatcher: Dispatcher,
    ) -> None:
        self._lgr = lgr
        self._dispatcher = dispatcher

        self._uow = uow.UOW(store)
        self._repo: uow.Repo | None = None
        self._events: list[fsm.Event] = []

    async def __aenter__(self) -> Self:
        self._repo = await self._uow.__aenter__()

        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        await self._uow.__aexit__(exc_type, exc_value, traceback)

        if exc_type is None:
            for event in self._events:
                self._dispatcher.send(event)
                self._lgr.info(f"Sending {event}")

    @property
    def _entered_repo(self) -> uow.Repo:
        if self._repo is None:
            raise errors.ControllersError("Tx used outside of a transaction")

        return self._repo

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
        return await self._entered_repo.get(t_entity, uid)

    async def get_for_update[E: domain.Object](
        self,
        t_entity: type[E],
        uid: domain.UID | None = None,
    ) -> E:
        return await self._entered_repo.get_for_update(t_entity, uid)

    async def delete(self, entity: domain.Object) -> None:
        await self._entered_repo.delete(entity)

    async def count_models(self) -> int:
        return await self._entered_repo.count_models()

    async def next_model_for_update(self) -> tuple[evolve.Model, float]:
        return await self._entered_repo.next_model_for_update()

    async def delete_worst_model(self) -> int:
        return await self._entered_repo.delete_worst_model()

    async def get_models(self, day: domain.Day) -> list[evolve.Model]:
        return await self._entered_repo.get_models(day)

    async def sample_models(self, n: int) -> list[evolve.Model]:
        return await self._entered_repo.sample_models(n)

    def get_all[E: domain.Object](
        self,
        t_entity: type[E],
    ) -> AsyncIterator[E]:
        return self._entered_repo.get_all(t_entity)

    async def drop(self, entity_type: type[domain.Object]) -> None:
        await self._entered_repo.drop(entity_type)
