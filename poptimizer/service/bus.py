from poptimizer.adapters import msg
from poptimizer.handlers import handler
from poptimizer.handlers.data import trading_day
from poptimizer.handlers.evolve import evolve


def run(bus: msg.Bus) -> None:
    bus.add_event_handler(trading_day.TradingDayHandler(bus), msg.IndefiniteRetryPolicy)
    bus.add_event_handler(evolve.EvolutionHandler(bus), msg.IndefiniteRetryPolicy)
    bus.publish(handler.TradingDayCheckRequired())
