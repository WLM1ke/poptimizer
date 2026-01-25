import asyncio
import logging
from collections.abc import Callable, Iterable
from types import TracebackType
from typing import NewType, Protocol, Self, get_args, get_type_hints

from pydantic import BaseModel

from poptimizer.domain import domain
from poptimizer.domain.evolve import evolve

PID = NewType("PID", int)


class Message(BaseModel): ...


class State(domain.Entity): ...


class _Ctx(Protocol):
    def send(self, pid: PID, msg: Message) -> None: ...

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


class _Handler[**I, O](Protocol):
    async def __call__(self, ctx: _Ctx, *args: I.args, **kwargs: I.kwargs) -> O: ...


class _UOW(Protocol):
    async def run[**I, O](self, handler: _Handler[I, O], *args: I.args, **kwargs: I.kwargs) -> None: ...
    def outbox(self) -> Iterable[tuple[PID, Message]]: ...


class _Actor[S: State, M: Message](Protocol):
    async def __call__(self, ctx: _Ctx, state: S, msg: M) -> None: ...


class _Inbox:
    def __init__(self, pid: PID) -> None:
        self._pid = pid
        self._inbox = asyncio.Queue[Message]()

    @property
    def pid(self) -> PID:
        return self._pid

    def send(self, msg: Message) -> None:
        self._inbox.put_nowait(msg)

    async def get(self) -> Message:
        return await self._inbox.get()


class _Dispatcher:
    def __init__(self) -> None:
        self._lgr = logging.getLogger()
        self._last_pid = 0
        self._inboxes = dict[int, _Inbox]()

    def new_inbox(self) -> _Inbox:
        self._last_pid += 1
        inbox = _Inbox(PID(self._last_pid))
        self._inboxes[inbox.pid] = inbox

        return inbox

    def send(self, pid: PID, msg: Message) -> None:
        match inbox := self._inboxes.get(pid):
            case _Inbox():
                inbox.send(msg)
            case None:
                self._lgr.warning("Unknown inbox %d", pid)


class System:
    def __init__(self, uow_factory: Callable[[], _UOW]) -> None:
        self._lgr = logging.getLogger()
        self._uow_factory = uow_factory
        self._dispatcher = _Dispatcher()
        self._tg = asyncio.TaskGroup()

    async def __aenter__(self) -> Self:
        await self._tg.__aenter__()

        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        return await self._tg.__aexit__(exc_type, exc_value, traceback)

    async def run[S: State, M: Message](self, actor: _Actor[S, M]) -> PID:
        inbox = self._dispatcher.new_inbox()

        self._tg.create_task(self._loop(actor, inbox))

        return inbox.pid

    async def _loop[S: State, M: Message](self, actor: _Actor[S, M], inbox: _Inbox) -> None:
        while True:
            uow = self._uow_factory()

            await uow.run(self._run, actor, await inbox.get())

            for pid, out_msg in uow.outbox():
                self._dispatcher.send(pid, out_msg)

    async def _run[S: State, M: Message](
        self,
        ctx: _Ctx,
        actor: _Actor[S, M],
        msg: Message,
    ) -> None:
        state_type, msg_type = _actor_types(actor)
        if not isinstance(msg, msg_type):
            self._lgr.warning("Unknown inbox message %s for actor %s", msg, actor.__class__.__name__)

            return

        state = await ctx.get_for_update(state_type)
        await actor(ctx, state, msg)


def _actor_types[S: State, M: Message](actor: _Actor[S, M]) -> tuple[type[S], tuple[type[M]]]:
    type_hints = get_type_hints(actor)

    state_type = type_hints["state"]

    msg_type_union = get_args(type_hints["msg"])
    if not msg_type_union:
        msg_type_union = (type_hints["msg"],)

    return state_type, msg_type_union
