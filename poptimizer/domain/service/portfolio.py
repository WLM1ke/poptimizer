import asyncio
from collections.abc import Callable
from datetime import date
from typing import Final, Self

import numpy as np
import pandas as pd
from pydantic import BaseModel, NonNegativeInt, PositiveFloat, PositiveInt

from poptimizer.domain.entity import entity, portfolio
from poptimizer.domain.entity.data import securities
from poptimizer.domain.service import domain_service

_START_LIQUIDITY_DAYS: Final = 21
_MINIMUM_HISTORY: Final = 30 * 21


class PortfolioUpdateService:
    async def __call__(self, ctx: domain_service.VCtx, update_day: entity.Day) -> None:
        port = await ctx.get_for_update(portfolio.Portfolio)

        sec_data = await _prepare_sec_data(ctx, update_day)

        _remove_not_traded(ctx, port, sec_data)
        _update_sec_data(ctx, port, sec_data)
        _add_liquid(ctx, port, sec_data)
        port.day = update_day


async def _prepare_sec_data(
    ctx: domain_service.VCtx, update_day: entity.Day
) -> dict[entity.Ticker, portfolio.Security]:
    sec_table = await ctx.get(securities.Securities)

    tickers = tuple(sec.ticker for sec in sec_table.df)

    last_day_ts = pd.Timestamp(update_day)
    async with asyncio.TaskGroup() as tg:
        turnover_task = tg.create_task(ctx.viewer.turnover(last_day_ts, tickers))
        close_task = tg.create_task(ctx.viewer.close(last_day_ts, tickers))

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


def _remove_not_traded(
    ctx: domain_service.Ctx, port: portfolio.Portfolio, sec_data: dict[entity.Ticker, portfolio.Security]
) -> None:
    not_traded = port.securities.keys() - sec_data.keys()

    for ticker in not_traded:
        port.securities[ticker].turnover = 0

        match port.remove_ticket(ticker):
            case True:
                ctx.warn(f"Not traded {ticker} is removed")
            case False:
                ctx.warn(f"Not traded {ticker} is not removed")


def _update_sec_data(
    ctx: domain_service.Ctx,
    port: portfolio.Portfolio,
    sec_data: dict[entity.Ticker, portfolio.Security],
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
                ctx.warn(f"Not liquid {ticker} is removed")
            case False:
                ctx.warn(f"Not liquid {ticker} is not removed")


def _add_liquid(
    ctx: domain_service.Ctx,
    port: portfolio.Portfolio,
    sec_data: dict[entity.Ticker, portfolio.Security],
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

            ctx.warn(f"{ticker} is added")


class SecurityDTO(BaseModel):
    lot: PositiveInt
    price: PositiveFloat


class PortfolioDTO(BaseModel):
    day: date
    accounts: dict[entity.AccName, portfolio.Account]
    securities: dict[entity.Ticker, SecurityDTO]

    @classmethod
    def from_portfolio(cls, port: portfolio.Portfolio) -> Self:
        return cls(
            day=port.day,
            accounts=port.accounts,
            securities={ticker: SecurityDTO(lot=sec.lot, price=sec.price) for ticker, sec in port.securities.items()},
        )


class PositionDTO(BaseModel):
    name: entity.AccName
    ticker: entity.Ticker
    amount: NonNegativeInt


class PortfolioEditService:
    def __init__(self, optimization_action: Callable[[], None]) -> None:
        self._optimization_action = optimization_action

    async def get_portfolio(self, ctx: domain_service.Ctx) -> PortfolioDTO:
        port = await ctx.get(portfolio.Portfolio)

        return PortfolioDTO.from_portfolio(port)

    async def create_account(self, ctx: domain_service.Ctx, name: entity.AccName) -> PortfolioDTO:
        port = await ctx.get_for_update(portfolio.Portfolio)

        port.create_acount(entity.AccName(name))

        return PortfolioDTO.from_portfolio(port)

    async def remove_acount(self, ctx: domain_service.Ctx, name: entity.AccName) -> PortfolioDTO:
        port = await ctx.get_for_update(portfolio.Portfolio)

        port.remove_acount(entity.AccName(name))

        return PortfolioDTO.from_portfolio(port)

    async def update_position(
        self,
        ctx: domain_service.Ctx,
        position: PositionDTO,
    ) -> PortfolioDTO:
        port = await ctx.get_for_update(portfolio.Portfolio)

        port.update_position(
            position.name,
            position.ticker,
            position.amount,
        )

        self._optimization_action()

        return PortfolioDTO.from_portfolio(port)
