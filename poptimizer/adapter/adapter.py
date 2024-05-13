from typing import Any

from poptimizer.domain import consts


def get_component_name(component: Any) -> str:
    if isinstance(component, type):
        return component.__name__

    return component.__class__.__name__


class AdaptersError(consts.POError): ...
