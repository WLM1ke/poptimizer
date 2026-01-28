import types
from typing import Any, NewType, Protocol

from pydantic import BaseModel

from poptimizer.actors import run
from poptimizer.domain import domain
from poptimizer.domain.evolve import evolve

Component = NewType("Component", str)


def get_component_name(component: Any) -> Component:
    if isinstance(component, type):
        return Component(component.__name__)

    if isinstance(component, types.MethodType):
        return Component(component.__self__.__class__.__name__)

    return Component(component.__class__.__name__)


PID = NewType("PID", str)


class Message(BaseModel): ...


class State(domain.Entity): ...


class SubCtx(Protocol):
    async def run_with_retry[**I, O](
        self,
        handler: run.Handler[SubCtx, I, O],
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


class Actor[S: State, M: Message](Protocol):
    async def __call__(self, ctx: Ctx, state: S, msg: M) -> None: ...
