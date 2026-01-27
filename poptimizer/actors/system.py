import asyncio
import logging
from types import TracebackType
from typing import Protocol, Self, get_args, get_type_hints

from poptimizer.actors import actor, runner, tx, uow


class _Dispatcher:
    def __init__(self) -> None:
        self._lgr = logging.getLogger()
        self._last_pid = 0
        self._inboxes = dict[actor.PID, asyncio.Queue[actor.Message]()]()

    def new_inbox(self) -> tuple[actor.PID, asyncio.Queue[actor.Message]]:
        self._last_pid += 1

        inbox = asyncio.Queue[actor.Message]()
        pid = actor.PID(self._last_pid)
        self._inboxes[actor.PID(self._last_pid)] = inbox

        return pid, inbox

    def send(self, pid: actor.PID, msg: actor.Message) -> None:
        match inbox := self._inboxes.get(pid):
            case asyncio.Queue():
                inbox.put_nowait(msg)
            case None:
                self._lgr.warning("Unknown inbox %d", pid)


class Actor[S: actor.State, M: actor.Message](Protocol):
    async def __call__(self, ctx: actor.Ctx, state: S, msg: M) -> None: ...


class System:
    def __init__(self, repo: uow.Repo) -> None:
        self._lgr = logging.getLogger()
        self._repo = repo
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

    async def run[S: actor.State, M: actor.Message](self, actor: Actor[S, M]) -> actor.PID:
        pid, inbox = self._dispatcher.new_inbox()

        self._tg.create_task(self._loop(actor, pid, inbox))

        return pid

    async def _loop[S: actor.State, M: actor.Message](
        self,
        actor: Actor[S, M],
        pid: actor.PID,
        inbox: asyncio.Queue[actor.Message],
    ) -> None:
        while True:
            await runner.Runner().run_with_retry(
                self._run,
                tx.Tx(self._repo, self._dispatcher.send, pid),
                actor,
                await inbox.get(),
            )

    async def _run[S: actor.State, M: actor.Message](
        self,
        ctx: actor.Ctx,
        actor: Actor[S, M],
        msg: actor.Message,
    ) -> None:
        state_type, msg_type = _actor_types(actor)
        if not isinstance(msg, msg_type):
            self._lgr.warning("Unknown inbox message %s for actor %s", msg, actor.__class__.__name__)

            return

        state = await ctx.get_for_update(state_type)
        await actor(ctx, state, msg)


def _actor_types[S: actor.State, M: actor.Message](actor: Actor[S, M]) -> tuple[type[S], tuple[type[M]]]:
    type_hints = get_type_hints(actor)

    state_type = type_hints["state"]

    msg_type_union = get_args(type_hints["msg"])
    if not msg_type_union:
        msg_type_union = (type_hints["msg"],)

    return state_type, msg_type_union
