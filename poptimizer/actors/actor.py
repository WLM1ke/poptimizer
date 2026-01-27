from typing import NewType, Protocol

from pydantic import BaseModel

from poptimizer.actors import runner
from poptimizer.domain import domain
from poptimizer.domain.evolve import evolve

PID = NewType("PID", int)


class Message(BaseModel): ...


class State(domain.Entity): ...


class SubCtx(Protocol):
    async def run_with_retry[**I, O](
        self,
        handler: runner.Handler[SubCtx, I, O],
        *args: I.args,
        **kwargs: I.kwargs,
    ) -> O: ...

    async def get[E: domain.Entity](
        self,
        t_entity: type[E],
        uid: domain.UID | None = None,
    ) -> E: ...

    async def get_for_update[E: domain.Entity](
        self,
        t_entity: type[E],
        uid: domain.UID | None = None,
    ) -> E: ...

    async def delete(self, entity: domain.Entity) -> None: ...

    async def count_models(self) -> int: ...

    async def next_model_for_update(self, uid: domain.UID) -> tuple[evolve.Model, bool]: ...

    async def sample_models(self, n: int) -> list[evolve.Model]: ...


class Ctx(SubCtx, Protocol):
    def send(self, pid: PID, msg: Message) -> None: ...
    def send_self(self, msg: Message) -> None: ...
