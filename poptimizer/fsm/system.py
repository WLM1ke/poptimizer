import asyncio
import logging
import random
import traceback as tb
from datetime import timedelta
from types import TracebackType
from typing import Final, Self

from poptimizer.core import errors, fsm
from poptimizer.fsm import graph, tx, uow

_FIRST_RETRY: Final = timedelta(seconds=30)
_BACKOFF_FACTOR: Final = 2


class _Dispatcher:
    def __init__(self) -> None:
        self._inboxes = list[asyncio.Queue[fsm.Event]()]()

    def new_inbox(self) -> asyncio.Queue[fsm.Event]:
        self._inboxes.append(asyncio.Queue[fsm.Event]())

        return self._inboxes[-1]

    def send(self, event: fsm.Event) -> None:
        for inbox in self._inboxes:
            inbox.put_nowait(event)


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

    def start_fsm(self, graph: graph.Graph) -> None:
        self._tg.create_task(self._loop(graph, self._dispatcher.new_inbox()))

    def send(self, msg: fsm.Event) -> None:
        self._dispatcher.send(msg)

    async def _loop(
        self,
        graph: graph.Graph,
        inbox: asyncio.Queue[fsm.Event],
    ) -> None:
        lgr = logging.getLogger(graph.name)

        while True:
            event = await inbox.get()

            if action := graph.make_transition(event):
                await self._retry(
                    lgr,
                    action,
                    event,
                )

                lgr.info(f"Handled event {event}")

    async def _retry[E: fsm.Event](
        self,
        lgr: logging.Logger,
        action: graph.Action[E],
        event: E,
    ) -> None:
        delay = _FIRST_RETRY

        while True:
            err = await self._run_safe(lgr, action, event)
            if err is None:
                return

            lgr.info("Failed transition action with %s - retrying in %s", err, delay)
            await asyncio.sleep(delay.total_seconds())

            delay = _next_delay(delay)

    async def _run_safe[E: fsm.Event](
        self,
        lgr: logging.Logger,
        action: graph.Action[E],
        event: E,
    ) -> None | errors.POError:
        err_out: errors.POError = errors.POError()

        try:
            async with tx.Tx(lgr, self._repo, self._dispatcher) as ctx:
                return await action(ctx, event)
        except* errors.POError as err:
            tb.print_exception(err, colorize=True)  # type: ignore[reportCallIssue]

            err_out = errors.get_root_poptimizer_error(err)

        return err_out


def _next_delay(delay: timedelta) -> timedelta:
    return timedelta(seconds=delay.total_seconds() * _BACKOFF_FACTOR * 2 * random.random())  # noqa: S311
