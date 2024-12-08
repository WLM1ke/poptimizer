import asyncio
import logging
from typing import Protocol

import numpy as np
import pandas as pd

from poptimizer import consts
from poptimizer.domain import domain
from poptimizer.domain.evolve import evolve
from poptimizer.domain.moex import securities
from poptimizer.domain.portfolio import portfolio
from poptimizer.use_cases import handler


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

    async def __call__(self, ctx: handler.Ctx, msg: handler.DivUpdated) -> handler.PortfolioUpdated:
        port = await ctx.get_for_update(portfolio.Portfolio)

        sec_cache = await self._prepare_sec_cache(ctx, msg.day)
        min_turnover = _calc_min_turnover(port, sec_cache)

        self._update_existing_positions(port, sec_cache, min_turnover)
        self._add_new_liquid(port, sec_cache, min_turnover)
        port.day = msg.day

        return handler.PortfolioUpdated(day=msg.day)

    async def _prepare_sec_cache(
        self,
        ctx: handler.Ctx,
        update_day: domain.Day,
    ) -> dict[domain.Ticker, portfolio.Position]:
        sec_table = await ctx.get(securities.Securities)

        tickers = tuple(sec.ticker for sec in sec_table.df)

        last_day_ts = pd.Timestamp(update_day)
        async with asyncio.TaskGroup() as tg:
            turnover_task = tg.create_task(self._viewer.turnover(last_day_ts, tickers))
            close_task = tg.create_task(self._viewer.close(last_day_ts, tickers))
            history_days_task = tg.create_task(ctx.get(evolve.Evolution))

        turnover = await turnover_task
        close = await close_task
        quotes_days = ((await history_days_task).minimal_returns_days + 1) * 2

        turnover = (  # type: ignore[reportUnknownMemberType]
            turnover.iloc[-quotes_days:]  # type: ignore[reportUnknownMemberType]
            .sort_index(ascending=False)
            .expanding()
            .median()
            .iloc[consts.FORECAST_DAYS :]
            .min()
        )

        return {
            sec.ticker: portfolio.Position(
                ticker=sec.ticker,
                lot=sec.lot,
                price=close.loc[last_day_ts, sec.ticker],  # type: ignore[reportUnknownMemberType]
                turnover=turnover[sec.ticker],  # type: ignore[reportUnknownMemberType]
            )
            for sec in sec_table.df
            if not np.isnan(close.loc[last_day_ts, sec.ticker])  # type: ignore[reportUnknownMemberType]
        }

    def _update_existing_positions(
        self,
        port: portfolio.Portfolio,
        sec_cache: dict[domain.Ticker, portfolio.Position],
        min_turnover: float,
    ) -> None:
        updated_positions: list[portfolio.Position] = []

        for position in port.positions:
            match sec_cache.pop(position.ticker, None):
                case None if not position.accounts:
                    self._lgr.warning("Not traded %s is removed", position.ticker)
                case None:
                    position.turnover = 0
                    updated_positions.append(position)
                    self._lgr.warning("Not traded %s is not removed", position.ticker)
                case new_position if new_position.turnover < min_turnover and not position.accounts:
                    self._lgr.warning("Not liquid %s is removed", position.ticker)
                case new_position if new_position.turnover < min_turnover:
                    new_position.accounts = position.accounts
                    updated_positions.append(new_position)
                    self._lgr.warning("Not liquid %s is not removed", position.ticker)
                case new_position:
                    new_position.accounts = position.accounts
                    updated_positions.append(new_position)

        port.positions = updated_positions

    def _add_new_liquid(
        self,
        port: portfolio.Portfolio,
        sec_cache: dict[domain.Ticker, portfolio.Position],
        min_turnover: float,
    ) -> None:
        for ticker, position in sec_cache.items():
            if position.turnover > min_turnover:
                n, _ = port.find_position(position.ticker)
                port.positions.insert(n, position)
                self._lgr.warning("%s is added", ticker)


def _calc_min_turnover(
    port: portfolio.Portfolio,
    sec_cache: dict[domain.Ticker, portfolio.Position],
) -> float:
    min_turnover = sum(port.cash.values())
    for position in port.positions:
        price = position.price
        if new_position := sec_cache.get(position.ticker):
            price = new_position.price

        min_turnover = max(min_turnover, sum(position.accounts.values()) * price)

    return min_turnover
