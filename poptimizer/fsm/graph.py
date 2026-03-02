from typing import Any, Protocol

from poptimizer.core import errors, fsm


class EventAction[E: fsm.Event](Protocol):
    async def __call__(self, ctx: fsm.Ctx, event: E) -> None: ...


class SimpleAction(Protocol):
    async def __call__(self, ctx: fsm.Ctx) -> None: ...


type StateDesc = tuple[EventAction[Any] | SimpleAction | None, set[type[fsm.Event]]]


class Graph:
    def __init__(self, name: str, initial_state: type[fsm.Event]) -> None:
        self._name = name
        self._state = initial_state
        self._graph = dict[type[fsm.Event], StateDesc]()

    @property
    def name(self) -> str:
        return self._name

    @property
    def state(self) -> str:
        return self._state.__name__

    def register_event[E: fsm.Event](
        self,
        state: type[E],
        transitions: set[type[fsm.Event]] | None = None,
        action: EventAction[E] | SimpleAction | None = None,
    ) -> None:
        transitions = transitions or set()

        if state in self._graph:
            raise errors.ControllersError("state {state} already in graph")

        self._graph[state] = (action, transitions)

    def make_transition[E: fsm.Event](self, event: E) -> EventAction[E] | SimpleAction | None:
        if not (desc := self._graph.get(self._state)):
            raise errors.ControllersError(f"unknown current state {self._state}")

        _, transitions = desc

        next_state = event.__class__
        if next_state not in transitions:
            return None

        self._state = next_state

        if not (desc := self._graph.get(next_state)):
            raise errors.ControllersError(f"unknown next state {next_state}")

        action, _ = desc

        return action
