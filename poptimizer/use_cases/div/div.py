import asyncio
from collections.abc import Iterator

from poptimizer.actors.data.div.models import div, raw
from poptimizer.actors.data.moex.models import securities
from poptimizer.core import actors, consts, domain


class DivHandler:
    async def __call__(self, ctx: actors.Ctx) -> None:
        sec_table = await ctx.get(securities.Securities)

        async with asyncio.TaskGroup() as tg:
            for sec in sec_table.df:
                tg.create_task(self._update_one(ctx, domain.UID(sec.ticker)))

    async def _update_one(
        self,
        ctx: actors.Ctx,
        ticker: domain.UID,
    ) -> None:
        div_table = await ctx.get_for_update(div.Dividends, ticker)
        raw_table = await ctx.get(raw.DivRaw, ticker)

        rows = list(_prepare_rows(raw_table.df))

        div_table.update(rows)


def _prepare_rows(raw_list: list[raw.Row]) -> Iterator[div.Row]:
    div_amount = 0
    day = consts.START_DAY
    if raw_list:
        day = raw_list[0].day

    for row in raw_list:
        if row.day > day:
            yield div.Row(day=day, dividend=div_amount)

            day = row.day
            div_amount = 0

        div_amount += row.dividend

    if div_amount:
        yield div.Row(day=day, dividend=div_amount)
