import aiohttp

from poptimizer.adapters import adapter, mongo
from poptimizer.domain.data.div import raw
from poptimizer.handlers import handler
from poptimizer.handlers.data import cpi, index, quotes, securities, trading_day
from poptimizer.handlers.data.div import div
from poptimizer.handlers.evolve import evolve
from poptimizer.service.bus import backup, msg


def run(
    bus: msg.Bus,
    http_client: aiohttp.ClientSession,
    mongo_db: mongo.MongoDatabase,
) -> None:
    bus.register_handler(
        backup.BackupHandler(mongo_db[adapter.get_component_name(raw.DivRaw)]),
        msg.IndefiniteRetryPolicy,
    )

    trading_day_handler = trading_day.TradingDayHandler(http_client)
    bus.register_handler(trading_day_handler.check, msg.IndefiniteRetryPolicy)
    bus.register_handler(trading_day_handler.update, msg.IndefiniteRetryPolicy)

    bus.register_handler(cpi.CPIHandler(http_client), msg.IgnoreErrorsPolicy)
    bus.register_handler(index.IndexesHandler(http_client), msg.IndefiniteRetryPolicy)
    bus.register_handler(securities.SecuritiesHandler(http_client), msg.IndefiniteRetryPolicy)
    bus.register_handler(quotes.QuotesHandler(http_client), msg.IndefiniteRetryPolicy)
    bus.register_handler(div.DivHandler(), msg.IndefiniteRetryPolicy)

    bus.register_handler(evolve.EvolutionHandler(), msg.IndefiniteRetryPolicy)

    bus.publish(handler.AppStarted())
