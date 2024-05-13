from datetime import date

import aiohttp

from poptimizer.adapters import dag
from poptimizer.app import states
from poptimizer.core import domain
from poptimizer.data import cpi, div, indexes, portfolio, quotes, reestry, securities, status, trading_day, usd
from poptimizer.service import uow


class UpdateDataAction:
    def __init__(self, http_client: aiohttp.ClientSession, ctx_factory: uow.CtxFactory) -> None:
        self._http_client = http_client
        self._ctx_factory = ctx_factory

    async def __call__(self) -> states.States:
        async with self._ctx_factory() as ctx:
            trading_day_srv = trading_day.TradingDayService(self._http_client)
            update_day = await trading_day_srv.is_update_required(ctx)

        match update_day:
            case None:
                return states.States.EVOLUTION_STEP
            case date():
                data_update_dag = _prepare_data_update_dag(self._http_client, self._ctx_factory, update_day)
                await data_update_dag()

                return states.States.OPTIMIZATION


def _prepare_data_update_dag(
    http_client: aiohttp.ClientSession,
    ctx_factory: uow.CtxFactory,
    update_day: domain.Day,
) -> dag.Dag[domain.Day]:
    data_update_dag = dag.Dag(ctx_factory, update_day)

    data_update_dag.add_node_ignore_errors(cpi.CPIUpdater(http_client))
    indexes_node = data_update_dag.add_node_with_retry(indexes.IndexesUpdater(http_client))
    securities_node = data_update_dag.add_node_with_retry(securities.SecuritiesUpdater(http_client))
    usd_node = data_update_dag.add_node_with_retry(usd.USDUpdater(http_client))

    quotes_node = data_update_dag.add_node_with_retry(quotes.QuotesUpdater(http_client), securities_node)
    div_node = data_update_dag.add_node_with_retry(div.DividendsUpdater(), securities_node, usd_node)

    port_node = data_update_dag.add_node_with_retry(portfolio.PortfolioUpdater(), quotes_node)

    div_status_node = data_update_dag.add_node_ignore_errors(status.DivStatusUpdater(http_client), port_node)
    data_update_dag.add_node_ignore_errors(reestry.ReestryDivUpdater(http_client), div_status_node)

    data_update_dag.add_node_with_retry(trading_day.TradingDayUpdater(), indexes_node, div_node, port_node)

    return data_update_dag
