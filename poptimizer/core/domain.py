from typing import Any, NewType, Protocol

from pydantic import BaseModel

Component = NewType("Component", str)


def get_component_name(component: Any) -> Component:
    return Component(component.__class__.__name__)


def get_component_name_for_type(component_type: type[Any]) -> Component:
    return Component(component_type.__name__)


class Ctx(Protocol):
    def info(self, msg: str) -> None: ...
    def warn(self, msg: str) -> None: ...


class State(BaseModel): ...
