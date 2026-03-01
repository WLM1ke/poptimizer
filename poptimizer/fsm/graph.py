from typing import Any, Protocol, get_args, get_type_hints

from poptimizer.core import errors, fsm


class Action[E: fsm.Event](Protocol):
    async def __call__(self, ctx: fsm.Ctx, event: E) -> None: ...


type StateDesc = tuple[Action[Any] | None, set[type[fsm.Event]]]


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
        action: Action[E] | None = None,
    ) -> None:
        transitions = transitions or set()

        if state in self._graph:
            raise errors.ControllersError("state {state} already in graph")

        self._graph[state] = (action, transitions)

    def make_transition[E: fsm.Event](self, event: E) -> Action[E] | None:
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

        if not action:
            return None

        if not isinstance(event, _action_event_types(action)):
            raise errors.ControllersError(f"can't handle {event.__class__.__name__} after transition to {next_state}")

        return action


def _action_event_types[E: fsm.Event](
    action: Action[E],
) -> tuple[type[E]]:
    type_hints = get_type_hints(action.__call__)

    msg_type_union = get_args(type_hints["event"])
    if not msg_type_union:
        msg_type_union = (type_hints["event"],)

    return msg_type_union
