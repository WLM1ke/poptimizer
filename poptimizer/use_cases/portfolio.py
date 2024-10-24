import asyncio
import logging
from typing import Final, Protocol

import numpy as np
import pandas as pd

from poptimizer.domain import domain, portfolio
from poptimizer.domain.data import securities
from poptimizer.use_cases import handler

_START_LIQUIDITY_DAYS: Final = 21
_MINIMUM_HISTORY: Final = 30 * 21


class Viewer(Protocol):
    async def close(
        self,
        last_day: pd.Timestamp,
        tickers: tuple[domain.Ticker, ...],
    ) -> pd.DataFrame: ...

    async def turnover(
        self,
        last_day: pd.Timestamp,
        tickers: tuple[domain.Ticker, ...],
    ) -> pd.DataFrame: ...


class PortfolioHandler:
    def __init__(self, viewer: Viewer) -> None:
        self._lgr = logging.getLogger()
        self._viewer = viewer

    async def __call__(self, ctx: handler.Ctx, msg: handler.DivUpdated) -> None:
        port = await ctx.get_for_update(portfolio.Portfolio)

        sec_data = await self._prepare_sec_data(ctx, msg.day)

        self._remove_not_traded(port, sec_data)
        self._update_sec_data(port, sec_data)
        self._add_liquid(port, sec_data)
        port.day = msg.day
        ctx.publish(handler.PortfolioUpdated(day=msg.day))

    async def _prepare_sec_data(
        self, ctx: handler.Ctx, update_day: domain.Day
    ) -> dict[domain.Ticker, portfolio.Security]:
        sec_table = await ctx.get(securities.Securities)

        tickers = tuple(sec.ticker for sec in sec_table.df)

        last_day_ts = pd.Timestamp(update_day)
        async with asyncio.TaskGroup() as tg:
            turnover_task = tg.create_task(self._viewer.turnover(last_day_ts, tickers))
            close_task = tg.create_task(self._viewer.close(last_day_ts, tickers))

        turnover = turnover_task.result()
        close = close_task.result()

        turnover = (  # type: ignore[reportUnknownMemberType]
            turnover.iloc[  # type: ignore[reportUnknownMemberType]
                -_MINIMUM_HISTORY * 2 :
            ]
            .sort_index(ascending=False)
            .expanding()
            .median()
            .iloc[_START_LIQUIDITY_DAYS:]
            .min()
        )

        return {
            sec.ticker: portfolio.Security(
                lot=sec.lot,
                price=close.loc[last_day_ts, sec.ticker],  # type: ignore[reportUnknownMemberType]
                turnover=turnover[sec.ticker],  # type: ignore[reportUnknownMemberType]
            )
            for sec in sec_table.df
            if not np.isnan(close.loc[last_day_ts, sec.ticker])  # type: ignore[reportUnknownMemberType]
        }

    def _remove_not_traded(self, port: portfolio.Portfolio, sec_data: dict[domain.Ticker, portfolio.Security]) -> None:
        not_traded = port.securities.keys() - sec_data.keys()

        for ticker in not_traded:
            port.securities[ticker].turnover = 0

            match port.remove_ticket(ticker):
                case True:
                    self._lgr.warning("Not traded %s is removed", ticker)
                case False:
                    self._lgr.warning("Not traded %s is not removed", ticker)

    def _update_sec_data(
        self,
        port: portfolio.Portfolio,
        sec_data: dict[domain.Ticker, portfolio.Security],
    ) -> None:
        min_turnover = port.value / (max(1, len(port.securities)))
        traded = port.securities.keys() & sec_data.keys()

        for ticker in traded:
            cur_data = port.securities[ticker]
            new_data = sec_data[ticker]

            cur_data.lot = new_data.lot
            cur_data.price = new_data.price
            cur_data.turnover = new_data.turnover

            if cur_data.turnover > min_turnover:
                continue

            match port.remove_ticket(ticker):
                case True:
                    self._lgr.warning("Not liquid %s is removed", ticker)
                case False:
                    self._lgr.warning("Not liquid %s is not removed", ticker)

    def _add_liquid(
        self,
        port: portfolio.Portfolio,
        sec_data: dict[domain.Ticker, portfolio.Security],
    ) -> None:
        min_turnover = port.value / (max(1, len(port.securities)))
        not_port = sec_data.keys() - port.securities.keys()

        for ticker in not_port:
            new_data = sec_data[ticker]

            if new_data.turnover > min_turnover:
                port.securities[ticker] = portfolio.Security(
                    lot=new_data.lot,
                    price=new_data.price,
                    turnover=new_data.turnover,
                )

                self._lgr.warning("%s is added", ticker)
