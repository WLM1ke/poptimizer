import asyncio
from datetime import date
from typing import Annotated, Protocol

from pydantic import AfterValidator, Field

from poptimizer.core import consts, domain, errors, fsms
from poptimizer.data.moex import securities


class Row(domain.Row):
    day: domain.Day = Field(alias="begin")
    open: float = Field(alias="open", gt=0)
    close: float = Field(alias="close", gt=0)
    high: float = Field(alias="high", gt=0)
    low: float = Field(alias="low", gt=0)
    turnover: float = Field(alias="value", ge=0)


class Quotes(domain.Entity):
    df: Annotated[
        list[Row],
        AfterValidator(domain.sorted_by_day_validator),
        AfterValidator(domain.after_start_date_validator),
    ] = Field(default_factory=list[Row])

    def update(self, rows: list[Row]) -> None:
        if not self.df:
            self.df = rows

            return

        last = self.df[-1]

        if last != (first := rows[0]):
            raise errors.DomainError(f"{self.uid} data mismatch {last} vs {first}")

        self.df.extend(rows[1:])

    def last_row_date(self) -> date | None:
        if not self.df:
            return None

        return self.df[-1].day


class Client(Protocol):
    async def get_quotes(
        self,
        ticker: domain.Ticker,
        start_day: domain.Day | None,
        end_day: domain.Day,
    ) -> list[Row]: ...


async def update(
    ctx: fsms.CoreCtx,
    moex_client: Client,
    update_day: domain.Day,
    sec_task: asyncio.Task[securities.Securities],
) -> None:
    trading_days: set[domain.Day] = set()
    sec_table = await sec_task

    async with asyncio.TaskGroup() as tg:
        for sec in sec_table.df:
            tg.create_task(_update_one(ctx, moex_client, sec.ticker, update_day, trading_days))

    sec_table.update_trading_days(trading_days)


async def _update_one(
    ctx: fsms.CoreCtx,
    moex_client: Client,
    ticker: domain.Ticker,
    update_day: domain.Day,
    trading_days: set[domain.Day],
) -> None:
    table = await ctx.get_for_update(Quotes, domain.UID(ticker))

    start_day = table.last_row_date() or consts.START_DAY
    rows = await moex_client.get_quotes(ticker, start_day, update_day)

    table.update(rows)

    trading_days.update(row.day for row in table.df)
