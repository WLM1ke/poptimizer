import asyncio
from typing import Final, NewType, Self

import numpy as np
import pandas as pd
from pydantic import BaseModel, Field, NonNegativeFloat, NonNegativeInt, PositiveFloat, PositiveInt, model_validator

from poptimizer.core import domain, errors
from poptimizer.data import data, securities

_START_LIQUIDITY_DAYS: Final = 21
_MINIMUM_HISTORY: Final = 30 * 21

_CashTicker: Final = domain.Ticker("CASH")

AccName = NewType("AccName", str)


class Account(BaseModel):
    cash: NonNegativeInt = 0
    positions: dict[domain.Ticker, PositiveInt] = Field(default_factory=dict)


class _Security(BaseModel):
    lot: PositiveInt
    price: PositiveFloat
    turnover: NonNegativeFloat


class Portfolio(domain.Entity):
    accounts: dict[AccName, Account] = Field(default_factory=dict)
    securities: dict[domain.Ticker, _Security] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _positions_are_multiple_of_lots(self) -> Self:
        for name, account in self.accounts.items():
            for ticker, shares in account.positions.items():
                if shares % (lot := self.securities[ticker].lot):
                    raise ValueError(f"{name} has {shares} {ticker} - not multiple of {lot} shares lot")

        return self

    @model_validator(mode="after")
    def _account_has_known_tickers(self) -> Self:
        for name, account in self.accounts.items():
            if unknown_tickers := account.positions.keys() - self.securities.keys():
                raise ValueError(f"{name} has {unknown_tickers}")

        return self

    @property
    def value(self) -> float:
        value = 0
        for account in self.accounts.values():
            value += account.cash

            for ticker, shares in account.positions.items():
                value += shares * self.securities[ticker].price

        return value

    def create_acount(self, name: AccName) -> None:
        if name in self.accounts:
            raise errors.DomainError(f"account {name} already exists")

        if not name:
            raise errors.DomainError("account name is empty")

        self.accounts[name] = Account()

    def remove_acount(self, name: AccName) -> None:
        account = self.accounts.pop(name, None)
        if account is None:
            raise errors.DomainError(f"account {name} doesn't exist")

        if account.cash or account.positions:
            self.accounts[name] = account

            raise errors.DomainError(f"account {name} is not empty")

    def remove_ticket(self, ticker: domain.Ticker) -> bool:
        for account in self.accounts.values():
            if ticker in account.positions:
                return False

        self.securities.pop(ticker)

        return True

    def update_position(self, name: AccName, ticker: domain.Ticker, amount: NonNegativeInt) -> None:
        if (account := self.accounts.get(name)) is None:
            raise errors.DomainError(f"account {name} doesn't exist")

        if ticker != _CashTicker and ticker not in self.securities:
            raise errors.DomainError(f"ticker {ticker} doesn't exist")

        if ticker == _CashTicker:
            account.cash = amount

            return

        if amount % (lot := self.securities[ticker].lot):
            raise errors.DomainError(f"amount {amount} must be multiple of {lot}")

        if not amount:
            account.positions.pop(ticker, None)

            return

        account.positions[ticker] = amount


class PortfolioUpdater:
    async def __call__(self, ctx: domain.Ctx, state: data.LastUpdate) -> None:
        port = await ctx.get(Portfolio)

        sec_data = await _prepare_sec_data(ctx, state.day)

        _remove_not_traded(ctx, port, sec_data)
        _update_sec_data(ctx, port, sec_data)
        _add_liquid(ctx, port, sec_data)
        port.day = state.day


async def _prepare_sec_data(ctx: domain.Ctx, last_day: domain.Day) -> dict[domain.Ticker, _Security]:
    sec_table = await ctx.get(securities.Securities, for_update=False)

    tickers = tuple(sec.ticker for sec in sec_table.df)

    last_day_ts = pd.Timestamp(last_day)
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
        sec.ticker: _Security(
            lot=sec.lot,
            price=close.loc[last_day_ts, sec.ticker],  # type: ignore[reportUnknownMemberType]
            turnover=turnover[sec.ticker],  # type: ignore[reportUnknownMemberType]
        )
        for sec in sec_table.df
        if not np.isnan(close.loc[last_day_ts, sec.ticker])  # type: ignore[reportUnknownMemberType]
    }


def _remove_not_traded(ctx: domain.Ctx, port: Portfolio, sec_data: dict[domain.Ticker, _Security]) -> None:
    not_traded = port.securities.keys() - sec_data.keys()

    for ticker in not_traded:
        port.securities[ticker].turnover = 0

        match port.remove_ticket(ticker):
            case True:
                ctx.warn(f"Not traded {ticker} is removed")
            case False:
                ctx.warn(f"Not traded {ticker} is not removed")


def _update_sec_data(ctx: domain.Ctx, port: Portfolio, sec_data: dict[domain.Ticker, _Security]) -> None:
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


def _add_liquid(ctx: domain.Ctx, port: Portfolio, sec_data: dict[domain.Ticker, _Security]) -> None:
    min_turnover = port.value / (max(1, len(port.securities)))
    not_port = sec_data.keys() - port.securities.keys()

    for ticker in not_port:
        new_data = sec_data[ticker]

        if new_data.turnover > min_turnover:
            port.securities[ticker] = _Security(
                lot=new_data.lot,
                price=new_data.price,
                turnover=new_data.turnover,
            )

            ctx.warn(f"{ticker} is added")
