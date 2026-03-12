import logging
from collections.abc import AsyncIterator
from types import TracebackType
from typing import Any, Protocol, Self

from poptimizer.core import domain, fsm
from poptimizer.evolve.evolution import evolve
from poptimizer.fsm import uow


class _Sender(Protocol):
    def send(self, event: fsm.Event) -> None: ...


class Tx:
    def __init__(
        self,
        lgr: logging.Logger,
        repo: uow.Repo,
        sender: _Sender,
    ) -> None:
        self._lgr = lgr
        self._repo = repo
        self._sender = sender

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
                self._sender.send(event)
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

    async def next_model(self) -> domain.UID:
        return await self._uow.next_model()

    async def sample_models(self, n: int) -> list[evolve.Model]:
        return await self._uow.sample_models(n)

    def get_all[E: domain.Object](
        self,
        t_entity: type[E],
    ) -> AsyncIterator[E]:
        return self._uow.get_all(t_entity)

    async def drop(self, entity_type: type[domain.Object]) -> None:
        await self._uow.drop(entity_type)
