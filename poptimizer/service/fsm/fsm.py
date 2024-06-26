import asyncio
from collections.abc import Awaitable, Callable
from enum import StrEnum
from typing import TypedDict

from poptimizer.service.common import logging, service

type States = StrEnum
type Action[S: States] = Callable[[], Awaitable[S]]
type Transitions[S: States] = set[S]


class StateDescription[S: States](TypedDict):
    action: Action[S]
    transitions: Transitions[S]


type Graph[S: States] = dict[S, StateDescription[S]]


class FSM[S: States]:
    def __init__(self, logging_service: logging.Service, graph: Graph[S]) -> None:
        self._logging_service = logging_service
        self._graph = graph
        self._events_stream = asyncio.Queue[S]()
        self._running = False

    def put(self, next_state: S) -> None:
        self._events_stream.put_nowait(next_state)

    async def __call__(self) -> None:
        if self._running:
            raise service.ServiceError("can't run running fsm")

        self._running = True

        next_state = next(iter(self._graph))
        transitions = await self._enter_state(next_state)

        while next_state := await self._events_stream.get():
            match next_state in transitions:
                case True:
                    transitions = await self._enter_state(next_state)
                case False:
                    self._logging_service.info(f"No transitions to {next_state} - skipping")

            self._events_stream.task_done()

    async def _enter_state(self, state: S) -> Transitions[S]:
        self._logging_service.info(state)
        state_description = self._graph[state]
        action = state_description["action"]
        next_state = await action()
        self.put(next_state)

        return state_description["transitions"]
