import aiohttp

from poptimizer.app import dag, uow
from poptimizer.data import cpi, data, trading_day


async def run(
    http_client: aiohttp.ClientSession,
    ctx_factory: uow.CtxFactory,
) -> None:
    data_update_dag = dag.Dag(ctx_factory, data.LastUpdate())
    trading_day_node = data_update_dag.add_node_with_retry(trading_day.TradingDayChecker(http_client))
    data_update_dag.add_node_ignore_errors(cpi.CPIUpdater(http_client), trading_day_node)
    data_update_dag.add_node_with_retry(trading_day.TradingDayUpdater(), trading_day_node)
    await data_update_dag.run()
