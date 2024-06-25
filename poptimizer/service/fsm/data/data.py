from datetime import date

import aiohttp

from poptimizer.domain.entity import entity
from poptimizer.domain.service import (
    portfolio,
)
from poptimizer.domain.service.data import (
    cpi,
    index,
    quotes,
    securities,
    trading_day,
    usd,
)
from poptimizer.domain.service.data.div import (
    div,
    reestry,
    status,
)
from poptimizer.service.common import uow
from poptimizer.service.fsm import states
from poptimizer.service.fsm.data import dag


class UpdateDataAction:
    def __init__(self, http_client: aiohttp.ClientSession, ctx_factory: uow.CtxFactory) -> None:
        self._http_client = http_client
        self._ctx_factory = ctx_factory

    async def __call__(self) -> states.States:
        async with self._ctx_factory() as ctx:
            trading_day_srv = trading_day.TradingDayCheckService(self._http_client)
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
    update_day: entity.Day,
) -> dag.Dag[entity.Day]:
    data_update_dag = dag.Dag(ctx_factory, update_day)

    data_update_dag.add_node_ignore_errors(cpi.CPIUpdateService(http_client))
    indexes_node = data_update_dag.add_node_with_retry(index.IndexUpdateService(http_client))
    securities_node = data_update_dag.add_node_with_retry(securities.SecuritiesUpdateService(http_client))
    usd_node = data_update_dag.add_node_with_retry(usd.USDUpdateService(http_client))

    quotes_node = data_update_dag.add_node_with_retry(quotes.QuotesUpdateService(http_client), securities_node)
    div_node = data_update_dag.add_node_with_retry(div.DivUpdateService(), securities_node, usd_node)

    port_node = data_update_dag.add_node_with_retry(portfolio.PortfolioUpdateService(), quotes_node)

    div_status_node = data_update_dag.add_node_ignore_errors(status.DivUpdateService(http_client), port_node)
    data_update_dag.add_node_ignore_errors(reestry.DivUpdateService(http_client), div_status_node)

    data_update_dag.add_node_with_retry(trading_day.TradingDayUpdateService(), indexes_node, div_node, port_node)

    return data_update_dag
