from collections.abc import AsyncIterator
from typing import Any, NewType, Protocol

from pydantic import BaseModel

from poptimizer.core import domain
from poptimizer.domain.evolve import evolve

AID = NewType("AID", str)


class Message(BaseModel):
    def __str__(self) -> str:
        return self.__repr__()


class State(domain.Versioned):
    def __str__(self) -> str:
        return self.__repr__()


class Handler[C, **I, O](Protocol):
    async def __call__(self, ctx: C, *args: I.args, **kwargs: I.kwargs) -> O: ...


class CoreCtx(Protocol):
    def info(self, msg: str, *args: Any) -> None: ...
    def warning(self, msg: str, *args: Any) -> None: ...
    async def run_with_retry[**I, O](
        self,
        handler: Handler[CoreCtx, I, O],
        *args: I.args,
        **kwargs: I.kwargs,
    ) -> O: ...
    async def get[E: domain.Entity](
        self,
        t_entity: type[E],
        uid: domain.UID | None = None,
    ) -> E: ...
    async def get_for_update[E: domain.Entity](self, t_entity: type[E], uid: domain.UID | None = None) -> E: ...


class Ctx(CoreCtx, Protocol):
    async def count_models(self) -> int: ...
    async def next_model_for_update(self, uid: domain.UID) -> tuple[evolve.Model, bool]: ...
    async def sample_models(self, n: int) -> list[evolve.Model]: ...
    async def delete(self, entity: domain.Entity) -> None: ...
    def get_all[E: domain.Entity](self, t_entity: type[E]) -> AsyncIterator[E]: ...
    async def drop(self, entity_type: type[domain.Entity]) -> None: ...
    def send(self, msg: Message, aid: AID | None = None) -> None: ...


class Actor[S: State, M: Message](Protocol):
    async def __call__(self, ctx: Ctx, state: S, msg: M) -> None: ...
