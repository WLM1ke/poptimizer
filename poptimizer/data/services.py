import asyncio
import itertools
from collections.abc import Callable
from datetime import date
from enum import StrEnum, auto

from pydantic import BaseModel, Field, NonNegativeInt, field_validator

from poptimizer.core import domain
from poptimizer.data import portfolio, quotes, reestry, status


class Portfolio:
    async def get_portfolio(self, ctx: domain.Ctx) -> portfolio.PortfolioData:
        port = await ctx.get(portfolio.Portfolio, for_update=False)

        return port.get_portfolio_data()

    async def create_account(self, ctx: domain.Ctx, name: portfolio.AccName) -> portfolio.PortfolioData:
        port = await ctx.get(portfolio.Portfolio)

        port.create_acount(portfolio.AccName(name))

        return port.get_portfolio_data()

    async def remove_acount(self, ctx: domain.Ctx, name: portfolio.AccName) -> portfolio.PortfolioData:
        port = await ctx.get(portfolio.Portfolio)

        port.remove_acount(portfolio.AccName(name))

        return port.get_portfolio_data()

    async def update_position(
        self,
        ctx: domain.Ctx,
        name: portfolio.AccName,
        ticker: domain.Ticker,
        amount: NonNegativeInt,
    ) -> portfolio.PortfolioData:
        port = await ctx.get(portfolio.Portfolio)

        port.update_position(
            portfolio.AccName(name),
            domain.Ticker(ticker),
            amount,
        )

        return port.get_portfolio_data()


class DivTickers(BaseModel):
    tickers: list[domain.Ticker]


class DivCompStatus(StrEnum):
    EXTRA = auto()
    OK = auto()
    MISSED = auto()


class DivCompareRow(BaseModel):
    day: date
    dividend: float = Field(gt=0)
    currency: domain.Currency
    status: DivCompStatus

    def to_tuple(self) -> tuple[date, float, domain.Currency]:
        return self.day, self.dividend, self.currency


class DividendsData(BaseModel):
    dividends: list[DivCompareRow]

    @field_validator("dividends")
    def _sorted_by_date_div_currency(cls, dividends: list[DivCompareRow]) -> list[DivCompareRow]:
        day_pairs = itertools.pairwise(row.to_tuple() for row in dividends)

        if not all(day <= next_ for day, next_ in day_pairs):
            raise ValueError("raw dividends are not sorted")

        return dividends


class UpdateDividends(BaseModel):
    ticker: domain.Ticker
    dividends: list[status.RowRaw]


class Dividends:
    def __init__(self, div_backup_srv: Callable[[], None]) -> None:
        self._div_backup_srv = div_backup_srv

    async def get_div_tickers(self, ctx: domain.Ctx) -> DivTickers:
        table = await ctx.get(status.DivStatus, for_update=False)

        return DivTickers(tickers=[row.ticker for row in table.df])

    async def get_dividends(self, ctx: domain.Ctx, ticker: domain.Ticker) -> DividendsData:
        async with asyncio.TaskGroup() as tg:
            raw_task = tg.create_task(ctx.get(status.DivRaw, domain.UID(ticker), for_update=False))
            reestry_task = tg.create_task(ctx.get(reestry.DivReestry, domain.UID(ticker), for_update=False))

        raw_table = raw_task.result()
        reestry_table = reestry_task.result()
        compare = [
            DivCompareRow(
                day=row_source.day,
                dividend=row_source.dividend,
                currency=row_source.currency,
                status=DivCompStatus.MISSED,
            )
            for row_source in reestry_table.df
            if not raw_table.has_row(row_source)
        ]

        for raw_row in raw_table.df:
            row_status = DivCompStatus.EXTRA
            if reestry_table.has_row(raw_row):
                row_status = DivCompStatus.OK

            compare.append(
                DivCompareRow(
                    day=raw_row.day,
                    dividend=raw_row.dividend,
                    currency=raw_row.currency,
                    status=row_status,
                ),
            )

        compare.sort(key=lambda compare: compare.to_tuple())

        return DividendsData(dividends=compare)

    async def update_dividends(self, ctx: domain.Ctx, div_update: UpdateDividends) -> None:
        async with asyncio.TaskGroup() as tg:
            raw_task = tg.create_task(ctx.get(status.DivRaw, domain.UID(div_update.ticker)))
            quotes_task = tg.create_task(ctx.get(quotes.Quotes, domain.UID(div_update.ticker), for_update=False))

        raw_table = raw_task.result()
        quotes_table = quotes_task.result()
        first_day = quotes_table.df[0].day

        raw_table.update(
            quotes_table.day,
            [row for row in div_update.dividends if row.day >= first_day],
        )
        self._div_backup_srv()
