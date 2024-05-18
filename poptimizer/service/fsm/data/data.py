from datetime import date

import aiohttp

from poptimizer.domain.entity import entity
from poptimizer.domain.service import (
    cpi,
    div,
    div_reestry,
    div_status,
    index,
    portfolio,
    quotes,
    securities,
    trading_day,
    usd,
)
from poptimizer.service import uow
from poptimizer.service.data import dag
from poptimizer.service.fsm import states


class UpdateDataAction:
    def __init__(self, http_client: aiohttp.ClientSession, ctx_factory: uow.CtxFactory) -> None:
        self._http_client = http_client
        self._ctx_factory = ctx_factory

    async def __call__(self) -> states.States:
        async with self._ctx_factory() as ctx:
            trading_day_srv = trading_day.CheckService(self._http_client)
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

    data_update_dag.add_node_ignore_errors(cpi.UpdateService(http_client))
    indexes_node = data_update_dag.add_node_with_retry(index.UpdateService(http_client))
    securities_node = data_update_dag.add_node_with_retry(securities.UpdateService(http_client))
    usd_node = data_update_dag.add_node_with_retry(usd.UpdateService(http_client))

    quotes_node = data_update_dag.add_node_with_retry(quotes.UpdateService(http_client), securities_node)
    div_node = data_update_dag.add_node_with_retry(div.UpdateService(), securities_node, usd_node)

    port_node = data_update_dag.add_node_with_retry(portfolio.UpdateService(), quotes_node)

    div_status_node = data_update_dag.add_node_ignore_errors(div_status.UpdateService(http_client), port_node)
    data_update_dag.add_node_ignore_errors(div_reestry.UpdateService(http_client), div_status_node)

    data_update_dag.add_node_with_retry(trading_day.UpdateService(), indexes_node, div_node, port_node)

    return data_update_dag
