import logging
from collections.abc import AsyncIterator
from types import TracebackType
from typing import Any, Protocol, Self

from poptimizer.actors import uow
from poptimizer.core import actors, domain
from poptimizer.domain.evolve import evolve


class _Sender(Protocol):
    def send(self, msg: actors.Message) -> None: ...


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
        self._msgs: list[actors.Message] = []

    async def __aenter__(self) -> Self:
        self._uow.clear()
        self._msgs.clear()

        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if exc_type is None:
            await self._uow.save()

            for msg in self._msgs:
                self._sender.send(msg)

    def info(self, msg: str, *args: Any) -> None:
        self._lgr.info(msg, *args)

    def warning(self, msg: str, *args: Any) -> None:
        self._lgr.warning(msg, *args)

    def send(self, msg: actors.Message) -> None:
        self._msgs.append(msg)

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

    async def next_model_for_update(self, uid: domain.UID) -> tuple[evolve.Model, bool]:
        return await self._uow.next_model_for_update(uid)

    async def sample_models(self, n: int) -> list[evolve.Model]:
        return await self._uow.sample_models(n)

    def get_all[E: domain.Object](
        self,
        t_entity: type[E],
    ) -> AsyncIterator[E]:
        return self._uow.get_all(t_entity)

    async def drop(self, entity_type: type[domain.Object]) -> None:
        await self._uow.drop(entity_type)
