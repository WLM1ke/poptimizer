import asyncio
from collections.abc import Iterator
from typing import Annotated

from pydantic import AfterValidator, Field, PositiveFloat

from poptimizer.core import actors, consts, domain
from poptimizer.data.div.models import raw
from poptimizer.data.moex import securities


class Row(domain.Row):
    day: domain.Day
    dividend: PositiveFloat


class Dividends(domain.Entity):
    df: Annotated[
        list[Row],
        AfterValidator(domain.sorted_by_day_validator),
        AfterValidator(domain.after_start_date_validator),
    ] = Field(default_factory=list[Row])

    def update(self, rows: list[Row]) -> None:
        self.df = rows


async def update(
    ctx: actors.CoreCtx,
    sec_task: asyncio.Task[securities.Securities],
) -> None:
    async with asyncio.TaskGroup() as tg:
        for sec in (await sec_task).df:
            tg.create_task(_update_one(ctx, domain.UID(sec.ticker)))


async def _update_one(ctx: actors.CoreCtx, ticker: domain.UID) -> None:
    div_table = await ctx.get_for_update(Dividends, ticker)
    raw_table = await ctx.get(raw.DivRaw, ticker)

    rows = list(_prepare_rows(raw_table.df))

    div_table.update(rows)


def _prepare_rows(raw_list: list[raw.Row]) -> Iterator[Row]:
    div_amount = 0
    day = consts.START_DAY
    if raw_list:
        day = raw_list[0].day

    for row in raw_list:
        if row.day > day:
            yield Row(day=day, dividend=div_amount)

            day = row.day
            div_amount = 0

        div_amount += row.dividend

    if div_amount:
        yield Row(day=day, dividend=div_amount)
