import aiohttp

from poptimizer.controllers.bus import msg
from poptimizer.use_cases import cpi
from poptimizer.use_cases.div import div, reestry, status
from poptimizer.use_cases.dl.features import quotes as quotes_features
from poptimizer.use_cases.evolve import evolve
from poptimizer.use_cases.moex import data, index, quotes, securities, usd
from poptimizer.use_cases.portfolio import forecasts, portfolio


def register_handlers(
    bus: msg.Bus,
    http_client: aiohttp.ClientSession,
) -> None:
    bus.register_event_handler(data.DataHandler(http_client), msg.IndefiniteRetryPolicy)
    bus.register_event_handler(cpi.CPIHandler(http_client), msg.IgnoreErrorsPolicy)
    bus.register_event_handler(usd.USDHandler(http_client), msg.IgnoreErrorsPolicy)
    bus.register_event_handler(index.IndexesHandler(http_client), msg.IndefiniteRetryPolicy)
    bus.register_event_handler(securities.SecuritiesHandler(http_client), msg.IndefiniteRetryPolicy)
    bus.register_event_handler(quotes.QuotesHandler(http_client), msg.IndefiniteRetryPolicy)
    bus.register_event_handler(div.DivHandler(), msg.IndefiniteRetryPolicy)
    bus.register_event_handler(portfolio.PortfolioHandler(), msg.IndefiniteRetryPolicy)
    bus.register_event_handler(quotes_features.QuotesFeatHandler(), msg.IndefiniteRetryPolicy)
    bus.register_event_handler(status.DivStatusHandler(http_client), msg.IgnoreErrorsPolicy)
    bus.register_event_handler(reestry.ReestryHandler(http_client), msg.IgnoreErrorsPolicy)
    bus.register_event_handler(evolve.EvolutionHandler(), msg.IndefiniteRetryPolicy)
    bus.register_event_handler(forecasts.ForecastHandler(), msg.IndefiniteRetryPolicy)
