from typing import Final

from poptimizer.adapters import message
from poptimizer.core import domain
from poptimizer.evolve import evolution

_EVOLUTION: Final = domain.Subdomain("evolve")


def init_subdomain(
    bus: message.Bus,
) -> None:
    bus.add_event_handler(
        _EVOLUTION,
        evolution.EvolutionEventHandler(),
        message.IndefiniteRetryPolicy,
    )
