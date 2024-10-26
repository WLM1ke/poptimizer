import aiohttp

from poptimizer.adapters import adapter, mongo
from poptimizer.controllers.bus import backup, msg
from poptimizer.domain.div import raw
from poptimizer.use_cases import cpi, portfolio, view
from poptimizer.use_cases.div import div, reestry, status
from poptimizer.use_cases.evolve import evolve
from poptimizer.use_cases.moex import index, quotes, securities, trading_day, usd


async def run(
    http_client: aiohttp.ClientSession,
    mongo_db: mongo.MongoDatabase,
) -> None:
    repo = mongo.Repo(mongo_db)
    viewer = view.Viewer(repo)
    bus = msg.Bus(repo)

    bus.register_event_handler(
        backup.BackupHandler(mongo_db[adapter.get_component_name(raw.DivRaw)]),
        msg.IndefiniteRetryPolicy,
    )

    trading_day_handler = trading_day.TradingDayHandler(http_client)
    bus.register_event_handler(trading_day_handler.check, msg.IndefiniteRetryPolicy)
    bus.register_event_handler(cpi.CPIHandler(http_client), msg.IgnoreErrorsPolicy)
    bus.register_event_handler(usd.USDHandler(http_client), msg.IgnoreErrorsPolicy)
    bus.register_event_handler(index.IndexesHandler(http_client), msg.IndefiniteRetryPolicy)
    bus.register_event_handler(securities.SecuritiesHandler(http_client), msg.IndefiniteRetryPolicy)
    bus.register_event_handler(quotes.QuotesHandler(http_client), msg.IndefiniteRetryPolicy)
    bus.register_event_handler(div.DivHandler(), msg.IndefiniteRetryPolicy)
    bus.register_event_handler(portfolio.PortfolioHandler(viewer), msg.IndefiniteRetryPolicy)
    bus.register_event_handler(status.DivStatusHandler(http_client), msg.IgnoreErrorsPolicy)
    bus.register_event_handler(reestry.ReestryHandler(http_client), msg.IgnoreErrorsPolicy)
    bus.register_event_handler(trading_day_handler.update, msg.IndefiniteRetryPolicy)

    bus.register_event_handler(evolve.EvolutionHandler(), msg.IndefiniteRetryPolicy)

    await bus.run()
