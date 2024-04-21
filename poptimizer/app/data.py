import asyncio
from datetime import date, timedelta
from typing import Final

import aiohttp

from poptimizer.app import dag, uow
from poptimizer.core import domain
from poptimizer.data import cpi, div, indexes, portfolio, quotes, reestry, securities, status, trading_day, usd

_POLLING_INTERVAL: Final = timedelta(minutes=10)


async def run(
    http_client: aiohttp.ClientSession,
    ctx_factory: uow.CtxFactory,
) -> None:
    trading_day_srv = trading_day.TradingDayService(http_client)

    while True:
        ctx = ctx_factory()
        async with ctx:
            update_day = await trading_day_srv.is_update_required(ctx)

        match update_day:
            case None:
                await asyncio.sleep(_POLLING_INTERVAL.total_seconds())
            case date():
                data_update_dag = _prepare_data_update_dag(http_client, ctx_factory, update_day)
                await data_update_dag()


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
