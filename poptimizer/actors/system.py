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
        self._inboxes = list[asyncio.Queue[actors.Message]()]()

    def new_inbox[S: actors.State[Any], M: actors.Message](self) -> asyncio.Queue[actors.Message]:
        self._inboxes.append(asyncio.Queue[actors.Message]())

        return self._inboxes[-1]

    def send(self, msg: actors.Message) -> None:
        for inbox in self._inboxes:
            inbox.put_nowait(msg)


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

    async def start[S: actors.State[Any], M: actors.Message](self, actor: actors.Actor[S, M]) -> None:
        self._tg.create_task(self._loop(actor, self._dispatcher.new_inbox()))

    def send(self, msg: actors.Message) -> None:
        self._dispatcher.send(msg)

    async def _loop[S: actors.State[Any], M: actors.Message](
        self,
        actor: actors.Actor[S, M],
        inbox: asyncio.Queue[actors.Message],
    ) -> None:
        lgr = logging.getLogger(actor.__class__.__name__)
        state_type, msg_type = _actor_types(actor)

        while True:
            msg = await inbox.get()

            if not isinstance(msg, msg_type):
                lgr.warning("Skipped unknown %r", msg)

                continue

            await self._retry(
                lgr,
                actor,
                state_type,
                msg,
            )

    async def _retry[S: actors.State[Any], M: actors.Message](
        self,
        lgr: logging.Logger,
        actor: actors.Actor[S, M],
        state_type: type[S],
        msg: M,
    ) -> None:
        last_delay = _FIRST_RETRY / _BACKOFF_FACTOR

        while True:
            match await self._run_safe(lgr, actor, state_type, msg):
                case errors.POError() as err:
                    last_delay = await _next_delay(last_delay)
                    lgr.info("Failed with %s - retrying in %s", err, last_delay)

                    await asyncio.sleep(last_delay.total_seconds())
                case output:
                    return output

    async def _run_safe[S: actors.State[Any], M: actors.Message](
        self,
        lgr: logging.Logger,
        actor: actors.Actor[S, M],
        state_type: type[S],
        msg: M,
    ) -> None | errors.POError:
        err_out: errors.POError = errors.POError()

        try:
            return await self._run(lgr, actor, state_type, msg)
        except* errors.POError as err:
            tb.print_exception(err, colorize=True)  # type: ignore[reportCallIssue]

            err_out = errors.get_root_poptimizer_error(err)

        return err_out

    async def _run[S: actors.State[Any], M: actors.Message](
        self,
        lgr: logging.Logger,
        actor: actors.Actor[S, M],
        state_type: type[S],
        msg: M,
    ) -> None:
        async with (
            tx.Tx(lgr, self._repo, self._dispatcher) as ctx_state,
            tx.Tx(lgr, self._repo, self._dispatcher) as ctx_entities,
        ):
            state = await ctx_state.get_for_update(state_type, domain.UID(state_type.__name__))
            await actor(ctx_entities, state, msg)

        lgr.info("Handled %s with state transition to %s", msg, state)


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
