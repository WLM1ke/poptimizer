from dataclasses import dataclass
from typing import Any, Protocol

from poptimizer.core import errors, fsm


class EventAction[E: fsm.Event](Protocol):
    async def __call__(self, ctx: fsm.Ctx, event: E) -> None: ...


class SimpleAction(Protocol):
    async def __call__(self, ctx: fsm.Ctx) -> None: ...


type State[E: fsm.Event] = type[E]
type Action[E: fsm.Event] = EventAction[E] | SimpleAction | None
type AfterTransition[S: fsm.Event, D: fsm.Event] = tuple[Action[S], State[D]]


@dataclass
class Transition[O: fsm.Event, D: fsm.Event]:
    on: type[O]
    dst: type[D]
    action: Action[O] | None = None


class Graph:
    def __init__(self, name: str) -> None:
        self._name = name
        self._state = fsm.Event
        self._graph = dict[State[Any], dict[State[Any], tuple[Action[Any], State[Any]]]]()

    @property
    def name(self) -> str:
        return self._name

    @property
    def state(self) -> str:
        return self._state.__name__

    def add_state(
        self,
        state: State[Any],
        transitions: list[Transition[Any, Any]] | None = None,
    ) -> None:
        if not self._graph:
            self._state = state

        if state in self._graph:
            raise errors.ControllersError("state {state} already in graph")

        self._graph[state] = {t.on: (t.action, t.dst) for t in transitions or ()}

    def make_transition[E: fsm.Event, D: fsm.Event](
        self,
        event: E,
    ) -> AfterTransition[E, Any] | None:
        if not (transitions := self._graph.get(self._state)):
            raise errors.ControllersError(f"unknown current state {self._state}")

        if (after_transition := transitions.get(event.__class__)) is None:
            return None

        action, self._state = after_transition

        return action, self._state
