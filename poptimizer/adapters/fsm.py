import asyncio
from collections.abc import Awaitable, Callable
from enum import StrEnum
from typing import NewType, TypedDict

from poptimizer.adapters import telegram
from poptimizer.core import errors

State = NewType("State", StrEnum)
Event = NewType("Event", StrEnum)

type Action[E: Event] = Callable[[], Awaitable[E]]


class StateDescription[S: State, E: Event](TypedDict):
    action: Action[E]
    transitions: dict[E, S]


type Graph[S: State, E: Event] = dict[S, StateDescription[S, E]]


class FSM[S: State, E: Event]:
    def __init__(self, logger: telegram.Logger, graph: Graph[S, E]) -> None:
        self._lgr = logger
        self._graph = graph
        self._events_stream = asyncio.Queue[E]()
        self._running = False

    def put(self, event: E) -> None:
        self._events_stream.put_nowait(event)

    async def __call__(self) -> None:
        if self._running:
            raise errors.AdaptersError("can't run running fsm")

        self._running = True

        current_state = next(iter(self._graph))
        self._lgr.info(f"Start -> {current_state}")
        state_transitions = await self._enter_state(current_state)

        while event := await self._events_stream.get():
            next_state = state_transitions.get(event)

            match next_state := state_transitions.get(event):
                case None:
                    self._lgr.info(f"Event {event} has no transitions")
                case _:
                    self._lgr.info(f"Event {event} -> {next_state}")
                    state_transitions = await self._enter_state(current_state)

    async def _enter_state(self, state: S) -> dict[E, S]:
        state_description = self._graph[state]
        event = await state_description["action"]()
        self.put(event)

        return state_description["transitions"]
