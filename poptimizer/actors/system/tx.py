import logging
from collections.abc import AsyncIterator
from types import TracebackType
from typing import Any, Protocol, Self

from poptimizer.actors.system import run, uow
from poptimizer.core import actors, domain
from poptimizer.domain.evolve import evolve


class _Sender(Protocol):
    def send(self, msg: actors.Message, aid: actors.AID) -> None: ...


class Tx:
    def __init__(
        self,
        lgr: logging.Logger,
        repo: uow.Repo,
        sender: _Sender,
        aid: actors.AID,
    ) -> None:
        self._lgr = lgr
        self._repo = repo
        self._sender = sender
        self._aid = aid

        self._uow = uow.UOW(repo)
        self._msgs: list[tuple[actors.Message, actors.AID]] = []

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

            for msg, aid in self._msgs:
                self._sender.send(msg, aid)

    def info(self, msg: str, *args: Any) -> None:
        self._lgr.info(msg, *args)

    def warning(self, msg: str, *args: Any) -> None:
        self._lgr.warning(msg, *args)

    def send(self, msg: actors.Message, aid: actors.AID | None = None) -> None:
        self._msgs.append((msg, aid or self._aid))

    async def run_with_retry[**I, O](
        self,
        handler: actors.Handler[actors.CoreCtx, I, O],
        *args: I.args,
        **kwargs: I.kwargs,
    ) -> O:
        tx = Tx(self._lgr, self._repo, self._sender, self._aid)

        return await run.with_retry(self._lgr, handler, tx, *args, **kwargs)

    async def get[E: domain.Versioned](
        self,
        t_entity: type[E],
        uid: domain.UID | None = None,
    ) -> E:
        return await self._uow.get(t_entity, uid)

    async def get_for_update[E: domain.Versioned](
        self,
        t_entity: type[E],
        uid: domain.UID | None = None,
    ) -> E:
        return await self._uow.get_for_update(t_entity, uid)

    async def delete(self, entity: domain.Versioned) -> None:
        await self._uow.delete(entity)

    async def count_models(self) -> int:
        return await self._uow.count_models()

    async def next_model_for_update(self, uid: domain.UID) -> tuple[evolve.Model, bool]:
        return await self._uow.next_model_for_update(uid)

    async def sample_models(self, n: int) -> list[evolve.Model]:
        return await self._uow.sample_models(n)

    def get_all[E: domain.Versioned](
        self,
        t_entity: type[E],
    ) -> AsyncIterator[E]:
        return self._uow.get_all(t_entity)

    async def drop(self, entity_type: type[domain.Versioned]) -> None:
        await self._uow.drop(entity_type)
