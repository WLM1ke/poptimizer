import asyncio
import logging
import random
from datetime import timedelta
from typing import Final, TypeIs, get_type_hints

from poptimizer.core import errors, fsm
from poptimizer.fsm import graph, tx, uow

_FIRST_RETRY: Final = timedelta(seconds=30)
_BACKOFF_FACTOR: Final = 2


class FSMSystem:
    def __init__(self, repo: uow.Repo, dispatcher: tx.Dispatcher) -> None:
        self._lgr = logging.getLogger(self.__class__.__name__)
        self._repo = repo
        self._dispatcher = dispatcher

    async def start(self, *graphs: graph.Graph) -> None:
        async with asyncio.TaskGroup() as tg:
            for graph in graphs:
                tg.create_task(self._loop(graph, self._dispatcher.new_inbox()))

            start_event = fsm.AppStarted()
            self._lgr.info(f"Sending {start_event}")
            self._dispatcher.send(start_event)

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
                errors.suppress_poptimizer(lgr, f"Retrying failed action in {delay}"),
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
