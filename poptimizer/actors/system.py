import asyncio
import logging
import random
import traceback as tb
from datetime import timedelta
from types import TracebackType
from typing import Any, Final, Self, get_args, get_type_hints

from poptimizer.actors import tx, uow
from poptimizer.core import actors, domain, errors

_FIRST_RETRY: Final = timedelta(seconds=30)
_BACKOFF_FACTOR: Final = 2


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
        ctx = tx.Tx(lgr, self._repo, self._dispatcher, aid)
        state_type, msg_type = _actor_types(actor)

        while True:
            msg = await inbox.get()

            if not isinstance(msg, msg_type):
                lgr.warning("Skipped unknown %r", msg)

                continue

            await self._retry(
                ctx,
                actor,
                state_type,
                msg,
            )

    async def _retry[S: actors.State[Any], M: actors.Message](
        self,
        tx: tx.Tx,
        actor: actors.Actor[S, M],
        state_type: type[S],
        msg: M,
    ) -> None:
        last_delay = _FIRST_RETRY / _BACKOFF_FACTOR

        while True:
            match await self._run_safe(tx, actor, state_type, msg):
                case errors.POError() as err:
                    last_delay = await _next_delay(last_delay)
                    tx.info("Failed with %s - retrying in %s", err, last_delay)

                    await asyncio.sleep(last_delay.total_seconds())
                case output:
                    return output

    async def _run_safe[S: actors.State[Any], M: actors.Message](
        self,
        tx: tx.Tx,
        actor: actors.Actor[S, M],
        state_type: type[S],
        msg: M,
    ) -> None | errors.POError:
        err_out: errors.POError = errors.POError()

        try:
            return await self._run(tx, actor, state_type, msg)
        except* errors.POError as err:
            tb.print_exception(err, colorize=True)  # type: ignore[reportCallIssue]

            err_out = errors.get_root_poptimizer_error(err)

        return err_out

    async def _run[S: actors.State[Any], M: actors.Message](
        self,
        tx: tx.Tx,
        actor: actors.Actor[S, M],
        state_type: type[S],
        msg: M,
    ) -> None:
        state, ver = await self._repo.get(state_type, domain.UID(state_type.__name__))

        async with tx as ctx:
            await actor(ctx, state, msg)

        await self._repo.save(state, ver)

        ctx.info("Handled %s with state transition to %s", msg, state)


def _actor_types[S: actors.State[Any], M: actors.Message](
    actor: actors.Actor[S, M],
) -> tuple[type[S], tuple[type[M]]]:
    type_hints = get_type_hints(actor.__call__)

    state_type = type_hints["state"]

    msg_type_union = get_args(type_hints["msg"])
    if not msg_type_union:
        msg_type_union = (type_hints["msg"],)

    return state_type, msg_type_union


async def _next_delay(delay: timedelta) -> timedelta:
    return timedelta(seconds=delay.total_seconds() * _BACKOFF_FACTOR * 2 * random.random())  # noqa: S311
