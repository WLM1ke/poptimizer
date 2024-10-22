import aiohttp

from poptimizer.adapters import msg
from poptimizer.handlers import handler
from poptimizer.handlers.data import trading_day
from poptimizer.handlers.evolve import evolve


def run(bus: msg.Bus, http_client: aiohttp.ClientSession) -> None:
    trading_day_handler = trading_day.TradingDayHandler(http_client)
    bus.register_handler(trading_day_handler.check, msg.IndefiniteRetryPolicy)
    bus.register_handler(trading_day_handler.update, msg.IndefiniteRetryPolicy)

    bus.register_handler(evolve.EvolutionHandler(), msg.IndefiniteRetryPolicy)
    bus.publish(handler.AppStarted())
