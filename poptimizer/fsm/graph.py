from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Protocol

from poptimizer.core import errors, fsm


class EventAction(Protocol):
    async def __call__(self, ctx: fsm.Ctx, event: fsm.Event) -> None: ...


class SimpleAction(Protocol):
    async def __call__(self, ctx: fsm.Ctx) -> None: ...


type State = type[fsm.Event]
type Action = Callable[..., Awaitable[None]] | None
type AfterTransition = tuple[Action, State]


@dataclass
class Transition:
    on: State
    dst: State
    action: Action = None


class Graph:
    def __init__(self, name: str) -> None:
        self._name = name
        self._state = fsm.Event
        self._graph: dict[State, dict[State, tuple[Action, State]]] = {}

    @property
    def name(self) -> str:
        return self._name

    @property
    def state(self) -> str:
        return self._state.__name__

    def add_state(
        self,
        state: State,
        transitions: list[Transition] | None = None,
    ) -> None:
        if not self._graph:
            self._state = state

        if state in self._graph:
            raise errors.ControllersError("state {state} already in graph")

        self._graph[state] = {t.on: (t.action, t.dst) for t in transitions or ()}

    def make_transition(
        self,
        event: fsm.Event,
    ) -> AfterTransition | None:
        if not (transitions := self._graph.get(self._state)):
            raise errors.ControllersError(f"unknown current state {self._state}")

        if (after_transition := transitions.get(event.__class__)) is None:
            return None

        action, self._state = after_transition

        return action, self._state
