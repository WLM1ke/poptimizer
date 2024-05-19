import asyncio
import bisect
from collections.abc import Iterator
from datetime import date

from poptimizer.domain import consts
from poptimizer.domain.entity import entity
from poptimizer.domain.entity.data import securities, usd
from poptimizer.domain.entity.data.div import div, div_raw
from poptimizer.domain.service import domain_service


class DividendsUpdateService:
    async def __call__(self, ctx: domain_service.Ctx, update_day: entity.Day) -> None:
        usd_table = await ctx.get(usd.USD)
        sec_table = await ctx.get(securities.Securities)

        async with asyncio.TaskGroup() as tg:
            for sec in sec_table.df:
                tg.create_task(self._update_one(ctx, update_day, entity.UID(sec.ticker), usd_table))

    async def _update_one(
        self,
        ctx: domain_service.Ctx,
        update_day: date,
        ticker: entity.UID,
        usd_table: usd.USD,
    ) -> None:
        div_table = await ctx.get(div.Dividends, ticker)
        raw_table = await ctx.get(div_raw.DivRaw, ticker)

        rows = list(_prepare_rows(raw_table.df, usd_table))

        div_table.update(update_day, rows)


def _prepare_rows(
    raw_list: list[div_raw.Row],
    usd_table: usd.USD,
) -> Iterator[div.Row]:
    div_amount = 0
    date = consts.START_DAY
    if raw_list:
        date = raw_list[0].day

    for row in raw_list:
        if row.day > date:
            yield div.Row(day=date, dividend=div_amount)

            date = row.day
            div_amount = 0

        div_amount += _div_in_rur(row, usd_table)

    if div_amount:
        yield div.Row(day=date, dividend=div_amount)


def _div_in_rur(raw_row: div_raw.Row, usd_table: usd.USD) -> float:
    match raw_row.currency:
        case entity.Currency.RUR:
            return raw_row.dividend
        case entity.Currency.USD:
            pos = bisect.bisect_right(usd_table.df, raw_row.day, key=lambda usd_row: usd_row.day)

            return raw_row.dividend * usd_table.df[pos - 1].close
