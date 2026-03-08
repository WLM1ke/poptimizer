import asyncio
import logging
import random
from datetime import timedelta
from types import TracebackType
from typing import Final, Self, TypeIs, get_type_hints

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


class FSMSystem:
    def __init__(self, repo: uow.Repo) -> None:
        self._lgr = logging.getLogger(self.__class__.__name__)
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

    def send(self, event: fsm.Event) -> None:
        self._lgr.info(f"Sending {event}")
        self._dispatcher.send(event)

    async def _loop(
        self,
        graph: graph.Graph,
        inbox: asyncio.Queue[fsm.Event],
    ) -> None:
        lgr = logging.getLogger(graph.name)
        lgr.info(f"Starting from {graph.state}")

        while True:
            event = await inbox.get()
            after_transition = graph.make_transition(event)
            if after_transition is None:
                continue

            action, destination = after_transition

            action_desc = "without action"
            if action:
                action_desc = f"with {action.__class__.__name__}()"

            if destination:
                lgr.info(f"Transition to {destination.__name__} {action_desc}")

            if action:
                await self._retry(
                    lgr,
                    action,
                    event,
                )

    async def _retry[E: fsm.Event](
        self,
        lgr: logging.Logger,
        action: graph.EventAction[E] | graph.SimpleAction,
        event: E,
    ) -> None:
        delay = _FIRST_RETRY

        while True:
            async with (
                errors.suppress_poptimizer(lgr, "Retrying failed action in %s"),
                tx.Tx(lgr, self._repo, self._dispatcher) as ctx,
            ):
                if _is_event_action(action):
                    return await action(ctx, event)

                return await action(ctx)

            await asyncio.sleep(delay.total_seconds())
            delay = _next_delay(delay)


def _next_delay(delay: timedelta) -> timedelta:
    return timedelta(seconds=delay.total_seconds() * _BACKOFF_FACTOR * 2 * random.random())  # noqa: S311


def _is_event_action[E: fsm.Event](action: graph.EventAction[E] | graph.SimpleAction) -> TypeIs[graph.EventAction[E]]:
    return "event" in get_type_hints(action.__call__)
