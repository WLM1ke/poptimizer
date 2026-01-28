import asyncio
import logging
from types import TracebackType
from typing import Self, get_args, get_type_hints

from poptimizer.actors.system import run, tx, uow
from poptimizer.core import actors


class _Dispatcher:
    def __init__(self) -> None:
        self._lgr = logging.getLogger()
        self._last_pid = 0
        self._inboxes = dict[actors.PID, asyncio.Queue[actors.Message]()]()

    def new_inbox[S: actors.State, M: actors.Message](
        self,
        actor: actors.Actor[S, M],
    ) -> tuple[actors.PID, asyncio.Queue[actors.Message]]:
        self._last_pid += 1
        name = actors.get_component_name(actor)

        inbox = asyncio.Queue[actors.Message]()
        pid = actors.PID(f"{name}-{self._last_pid}")
        self._inboxes[pid] = inbox

        return pid, inbox

    def send(self, pid: actors.PID, msg: actors.Message) -> None:
        match inbox := self._inboxes.get(pid):
            case asyncio.Queue():
                inbox.put_nowait(msg)
            case None:
                self._lgr.warning("Unknown inbox %d", pid)


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

    async def run[S: actors.State, M: actors.Message](self, actor: actors.Actor[S, M]) -> actors.PID:
        pid, inbox = self._dispatcher.new_inbox(actor)

        self._tg.create_task(self._loop(actor, pid, inbox))

        return pid

    async def _loop[S: actors.State, M: actors.Message](
        self,
        actor: actors.Actor[S, M],
        pid: actors.PID,
        inbox: asyncio.Queue[actors.Message],
    ) -> None:
        while True:
            await run.with_retry(
                self._run,
                tx.Tx(self._repo, self._dispatcher.send, pid),
                actor,
                pid,
                await inbox.get(),
            )

    async def _run[S: actors.State, M: actors.Message](
        self,
        ctx: actors.Ctx,
        actor: actors.Actor[S, M],
        pid: actors.PID,
        msg: actors.Message,
    ) -> None:
        state_type, msg_type = _actor_types(actor)
        if not isinstance(msg, msg_type):
            self._lgr.warning("Unknown inbox message %s for actor %s", msg, pid)

            return

        state = await ctx.get_for_update(state_type)
        await actor(ctx, state, msg)


def _actor_types[S: actors.State, M: actors.Message](actor: actors.Actor[S, M]) -> tuple[type[S], tuple[type[M]]]:
    type_hints = get_type_hints(actor)

    state_type = type_hints["state"]

    msg_type_union = get_args(type_hints["msg"])
    if not msg_type_union:
        msg_type_union = (type_hints["msg"],)

    return state_type, msg_type_union
