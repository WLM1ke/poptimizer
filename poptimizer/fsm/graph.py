from typing import Any, NewType, Protocol, get_args, get_type_hints

from poptimizer.core import errors, fsms

State = NewType("State", str)


class Action[E: fsms.Event](Protocol):
    async def __call__(self, ctx: fsms.Ctx, event: E) -> None: ...


type Transitions = dict[State, State]
type StateDesc = tuple[Action[Any] | None, Transitions]


class Graph:
    def __init__(self, name: str, initial_state: State) -> None:
        self._name = name
        self._state = initial_state
        self._graph = dict[State, StateDesc]()

    @property
    def name(self) -> str:
        return self._name

    @property
    def state(self) -> State:
        return self._state

    def register_state[E: fsms.Event](
        self,
        event_type: type[E],
        action: Action[E] | None,
        transitions: Transitions,
    ) -> None:
        state = State(event_type.__name__)

        if state in self._graph:
            raise errors.ControllersError("state {state} already in graph")

        self._graph[state] = (action, transitions)

    def make_transition[E: fsms.Event](self, event: E) -> Action[E] | None:
        if not (desc := self._graph.get(self._state)):
            raise errors.ControllersError(f"unknown current state {self._state}")

        _, transitions = desc

        if not (next_state := transitions.get(State(event.__class__.__name__))):
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


def _action_event_types[E: fsms.Event](
    action: Action[E],
) -> tuple[type[E]]:
    type_hints = get_type_hints(action.__call__)

    msg_type_union = get_args(type_hints["event"])
    if not msg_type_union:
        msg_type_union = (type_hints["msg"],)

    return msg_type_union
