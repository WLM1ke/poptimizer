import types
from typing import Any, NewType, cast

Component = NewType("Component", str)


def get_component_name(component: Any) -> Component:
    if isinstance(component, type):
        return Component(component.__name__)

    if isinstance(component, types.MethodType):
        return Component(component.__self__.__class__.__name__)

    return Component(component.__class__.__name__)


def get_root_error(exc: Exception) -> Exception:
    while isinstance(exc, ExceptionGroup):
        exc = cast("Exception", exc.exceptions[0])

    return exc
