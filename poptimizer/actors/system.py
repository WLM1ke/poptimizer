import asyncio
import logging
from types import TracebackType
from typing import Any, Self, get_args, get_type_hints

from poptimizer.actors import run, tx, uow
from poptimizer.core import actors


class _Dispatcher:
    def __init__(self) -> None:
        self._lgr = logging.getLogger()
        self._last_aid = 0
        self._inboxes = dict[actors.AID, asyncio.Queue[actors.Message]()]()

    def new_inbox[S: actors.State[Any], M: actors.Message](
        self,
        actor: actors.Actor[S, M],
    ) -> tuple[actors.AID, asyncio.Queue[actors.Message]]:
        self._last_aid += 1
        name = actor.__class__.__name__

        inbox = asyncio.Queue[actors.Message]()
        aid = actors.AID(f"{name}-{self._last_aid}")
        self._inboxes[aid] = inbox

        return aid, inbox

    def send(self, msg: actors.Message, aid: actors.AID) -> None:
        match inbox := self._inboxes.get(aid):
            case asyncio.Queue():
                inbox.put_nowait(msg)
            case None:
                self._lgr.warning("Unknown inbox %d", aid)


class System:
    def __init__(self, repo: uow.Repo) -> None:
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

    async def start[S: actors.State[Any], M: actors.Message](self, actor: actors.Actor[S, M]) -> actors.AID:
        aid, inbox = self._dispatcher.new_inbox(actor)

        self._tg.create_task(self._loop(actor, aid, inbox))

        return aid

    def send(self, msg: actors.Message, aid: actors.AID) -> None:
        self._dispatcher.send(msg, aid)

    async def _loop[S: actors.State[Any], M: actors.Message](
        self,
        actor: actors.Actor[S, M],
        aid: actors.AID,
        inbox: asyncio.Queue[actors.Message],
    ) -> None:
        lgr = logging.getLogger(actor.__class__.__name__)

        while True:
            msg = await inbox.get()
            state_type, msg_type = _actor_types(actor)

            if not isinstance(msg, msg_type):
                lgr.warning("skipped unknown %r", msg)

                continue

            await run.with_retry(
                lgr,
                _run,
                tx.Tx(lgr, self._repo, self._dispatcher, aid),
                actor,
                state_type,
                msg,
            )


async def _run[S: actors.State[Any], M: actors.Message](
    ctx: tx.Tx,
    actor: actors.Actor[S, M],
    state_type: type[S],
    msg: M,
) -> None:
    state = await ctx.get_for_update(state_type)
    initial_state = str(state)

    await actor(ctx, state, msg)

    ctx.info("Handled %s with state transition %s -> %s", msg, initial_state, state)


def _actor_types[S: actors.State[Any], M: actors.Message](
    actor: actors.Actor[S, M],
) -> tuple[type[S], tuple[type[M]]]:
    type_hints = get_type_hints(actor.__call__)

    state_type = type_hints["state"]

    msg_type_union = get_args(type_hints["msg"])
    if not msg_type_union:
        msg_type_union = (type_hints["msg"],)

    return state_type, msg_type_union
