import types
from typing import Any, NewType

from poptimizer.domain import domain


class Error(domain.POError): ...


Component = NewType("Component", str)


def get_component_name(component: Any) -> Component:
    if isinstance(component, type):
        return Component(component.__name__)

    if isinstance(component, types.MethodType):
        return Component(f"{component.__self__.__class__.__name__}.{component.__func__.__name__}")

    return Component(component.__class__.__name__)
