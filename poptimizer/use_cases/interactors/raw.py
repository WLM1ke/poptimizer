import asyncio
import itertools
from datetime import date
from enum import StrEnum, auto

from pydantic import Field, field_validator

from poptimizer.domain import domain
from poptimizer.domain.div import raw, reestry, status
from poptimizer.domain.moex import quotes
from poptimizer.use_cases import handler


class DivTickers(handler.DTO):
    tickers: list[domain.Ticker]


class DivCompStatus(StrEnum):
    EXTRA = auto()
    OK = auto()
    MISSED = auto()


class DivCompare(handler.DTO):
    day: date
    dividend: float = Field(gt=0)
    status: DivCompStatus

    def to_tuple(self) -> tuple[date, float]:
        return self.day, self.dividend


class Dividends(handler.DTO):
    dividends: list[DivCompare]

    @field_validator("dividends")
    def _sorted_by_date_div_currency(cls, dividends: list[DivCompare]) -> list[DivCompare]:
        day_pairs = itertools.pairwise(row.to_tuple() for row in dividends)

        if not all(day <= next_ for day, next_ in day_pairs):
            raise ValueError("raw dividends are not sorted")

        return dividends


class UpdateDividends(handler.DTO):
    ticker: domain.Ticker
    dividends: list[raw.Row]


class DividendsHandler:
    async def get_div_tickers(self, ctx: handler.Ctx) -> DivTickers:
        table = await ctx.get(status.DivStatus)

        return DivTickers(tickers=sorted({row.ticker for row in table.df}))

    async def get_dividends(self, ctx: handler.Ctx, ticker: domain.Ticker) -> Dividends:
        async with asyncio.TaskGroup() as tg:
            raw_task = tg.create_task(ctx.get(raw.DivRaw, domain.UID(ticker)))
            reestry_task = tg.create_task(ctx.get(reestry.DivReestry, domain.UID(ticker)))

        raw_table = await raw_task
        reestry_table = await reestry_task

        compare = [
            DivCompare(
                day=row_source.day,
                dividend=row_source.dividend,
                status=DivCompStatus.MISSED,
            )
            for row_source in reestry_table.df
            if not raw_table.has_row(raw.Row(day=row_source.day, dividend=row_source.dividend))
        ]

        for raw_row in raw_table.df:
            row_status = DivCompStatus.EXTRA
            if reestry_table.has_row(raw_row):
                row_status = DivCompStatus.OK

            compare.append(
                DivCompare(
                    day=raw_row.day,
                    dividend=raw_row.dividend,
                    status=row_status,
                ),
            )

        compare.sort(key=lambda compare: compare.to_tuple())

        return Dividends(dividends=compare)

    async def update_dividends(self, ctx: handler.Ctx, div_update: UpdateDividends) -> Dividends:
        async with asyncio.TaskGroup() as tg:
            raw_task = tg.create_task(ctx.get_for_update(raw.DivRaw, domain.UID(div_update.ticker)))
            quotes_task = tg.create_task(ctx.get(quotes.Quotes, domain.UID(div_update.ticker)))
            status_task = tg.create_task(ctx.get_for_update(status.DivStatus))

        raw_table = await raw_task
        quotes_table = await quotes_task
        status_table = await status_task

        first_day = quotes_table.df[0].day

        raw_table.update(
            quotes_table.day,
            [row for row in div_update.dividends if row.day >= first_day],
        )
        status_table.filter(raw_table)

        return await self.get_dividends(ctx, div_update.ticker)
