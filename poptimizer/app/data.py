import asyncio
from datetime import timedelta
from typing import Final

import aiohttp

from poptimizer.app import dag, uow
from poptimizer.data import cpi, data, indexes, securities, trading_day, usd

_POLLING_INTERVAL: Final = timedelta(minutes=10)


async def run(
    http_client: aiohttp.ClientSession,
    ctx_factory: uow.CtxFactory,
) -> None:
    trading_day_srv = trading_day.TradingDayService(http_client)

    while True:
        ctx = ctx_factory()
        async with ctx:
            last_update = await trading_day_srv.is_update_required(ctx)

        match last_update:
            case None:
                await asyncio.sleep(_POLLING_INTERVAL.total_seconds())
            case data.LastUpdate():
                data_update_dag = _prepare_data_update_dag(http_client, ctx_factory, last_update)
                await data_update_dag()
                ctx.info("Data update finished")


def _prepare_data_update_dag(
    http_client: aiohttp.ClientSession,
    ctx_factory: uow.CtxFactory,
    state: data.LastUpdate,
) -> dag.Dag[data.LastUpdate]:
    data_update_dag = dag.Dag(ctx_factory, state)

    data_update_dag.add_node_ignore_errors(cpi.CPIUpdater(http_client))
    indexes_node = data_update_dag.add_node_with_retry(indexes.IndexesUpdater(http_client))
    securities_node = data_update_dag.add_node_with_retry(securities.SecuritiesUpdater(http_client))
    usd_node = data_update_dag.add_node_with_retry(usd.USDUpdater(http_client))

    data_update_dag.add_node_with_retry(trading_day.TradingDayUpdater(), indexes_node, securities_node, usd_node)

    return data_update_dag
