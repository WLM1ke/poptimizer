from datetime import date

import aiohttp

from poptimizer.adapters import ctx
from poptimizer.app import dag
from poptimizer.data import cpi, data, trading_day


async def run(
    http_client: aiohttp.ClientSession,
    ctx_factory: ctx.Factory,
) -> None:
    data_update_dag = dag.Dag(ctx_factory, data.LastTradingDay(day=date(2020, 1, 1)))
    trading_day_node = data_update_dag.add_node_with_retry(trading_day.CheckTradingDay(http_client))
    data_update_dag.add_node(cpi.CPIUpdater(http_client), trading_day_node)
    data_update_dag.add_node_with_retry(trading_day.TradingDayUpdater(), trading_day_node)
    await data_update_dag.run()
