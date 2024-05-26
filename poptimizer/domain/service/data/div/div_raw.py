import asyncio
import itertools
from collections.abc import Callable
from datetime import date
from enum import StrEnum, auto

from pydantic import BaseModel, Field, field_validator

from poptimizer.domain.entity import entity
from poptimizer.domain.entity.data import quotes
from poptimizer.domain.entity.data.div import div_raw, div_reestry, div_status
from poptimizer.domain.service import domain_service


class DivTickersDTO(BaseModel):
    tickers: list[entity.Ticker]


class DivCompStatus(StrEnum):
    EXTRA = auto()
    OK = auto()
    MISSED = auto()


class DivCompareDTO(BaseModel):
    day: date
    dividend: float = Field(gt=0)
    currency: entity.Currency
    status: DivCompStatus

    def to_tuple(self) -> tuple[date, float, entity.Currency]:
        return self.day, self.dividend, self.currency


class DividendsDTO(BaseModel):
    dividends: list[DivCompareDTO]

    @field_validator("dividends")
    def _sorted_by_date_div_currency(cls, dividends: list[DivCompareDTO]) -> list[DivCompareDTO]:
        day_pairs = itertools.pairwise(row.to_tuple() for row in dividends)

        if not all(day <= next_ for day, next_ in day_pairs):
            raise ValueError("raw dividends are not sorted")

        return dividends


class UpdateDividends(BaseModel):
    ticker: entity.Ticker
    dividends: list[div_raw.Row]


class DividendsEditService:
    def __init__(self, div_backup_action: Callable[[], None]) -> None:
        self._div_backup_action = div_backup_action

    async def get_div_tickers(self, ctx: domain_service.Ctx) -> DivTickersDTO:
        table = await ctx.get(div_status.DivStatus)

        return DivTickersDTO(tickers=sorted({row.ticker for row in table.df}))

    async def get_dividends(self, ctx: domain_service.Ctx, ticker: entity.Ticker) -> DividendsDTO:
        async with asyncio.TaskGroup() as tg:
            raw_task = tg.create_task(ctx.get(div_raw.DivRaw, entity.UID(ticker)))
            reestry_task = tg.create_task(ctx.get(div_reestry.DivReestry, entity.UID(ticker)))

        raw_table = raw_task.result()
        reestry_table = reestry_task.result()
        compare = [
            DivCompareDTO(
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
                DivCompareDTO(
                    day=raw_row.day,
                    dividend=raw_row.dividend,
                    currency=raw_row.currency,
                    status=row_status,
                ),
            )

        compare.sort(key=lambda compare: compare.to_tuple())

        return DividendsDTO(dividends=compare)

    async def update_dividends(self, ctx: domain_service.Ctx, div_update: UpdateDividends) -> None:
        async with asyncio.TaskGroup() as tg:
            raw_task = tg.create_task(ctx.get_for_update(div_raw.DivRaw, entity.UID(div_update.ticker)))
            quotes_task = tg.create_task(ctx.get(quotes.Quotes, entity.UID(div_update.ticker)))
            status_task = tg.create_task(ctx.get_for_update(div_status.DivStatus))

        raw_table = raw_task.result()
        quotes_table = quotes_task.result()
        status_table = status_task.result()

        first_day = quotes_table.df[0].day

        raw_table.update(
            quotes_table.day,
            [row for row in div_update.dividends if row.day >= first_day],
        )
        status_table.filter(raw_table)

        self._div_backup_action()
