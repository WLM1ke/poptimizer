import asyncio
from datetime import date, timedelta
from typing import Annotated, Final, Protocol

from pydantic import AfterValidator, Field

from poptimizer.core import domain, errors, fsm

_MAX_INDEX_LAG: Final = timedelta(days=7)
RVI: Final = domain.Ticker("RVI")
IMOEX2: Final = domain.Ticker("IMOEX2")
MCF2TRR: Final = domain.Ticker("MCF2TRR")
RUGBITR1Y: Final = domain.Ticker("RUGBITR1Y")
INDEXES: Final = {
    MCF2TRR: domain.Ticker("MCFTRR"),
    domain.Ticker("MEFNTRR"): None,
    domain.Ticker("MEMMTRR"): None,
    domain.Ticker("MEOGTRR"): None,
    domain.Ticker("MESMTRR"): None,
    domain.Ticker("MOEX10"): None,
    IMOEX2: domain.Ticker("IMOEX"),
    RVI: None,
    RUGBITR1Y: None,
    domain.Ticker("RUGBITR5Y"): None,
    domain.Ticker("RUGBITR10Y"): None,
    domain.Ticker("RUCBITRL3"): None,
    domain.Ticker("MREDC"): None,
    domain.Ticker("RTSUSDCUR"): None,
}


class Row(domain.Row):
    day: domain.Day = Field(alias="begin")
    close: float = Field(alias="close", gt=0)


class Index(domain.Entity):
    df: Annotated[
        list[Row],
        AfterValidator(domain.sorted_by_day_validator),
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
    async def get_index(
        self,
        ticker: domain.Ticker,
        start_day: domain.Day | None,
        end_day: domain.Day,
    ) -> list[Row]: ...


async def update(
    ctx: fsm.Ctx,
    moex_client: Client,
    update_day: domain.Day,
) -> None:
    async with asyncio.TaskGroup() as tg:
        for ticker in INDEXES:
            tg.create_task(_update_one(ctx, moex_client, ticker, update_day))


async def _update_one(
    ctx: fsm.Ctx,
    moex_client: Client,
    ticker: domain.Ticker,
    update_day: domain.Day,
) -> None:
    table = await ctx.get_for_update(Index, domain.UID(ticker))

    start_day = table.last_row_date()
    rows = await moex_client.get_index(ticker, start_day, update_day)

    if start_day is None and (old_ticker := INDEXES[ticker]) is not None:
        first_rows = await moex_client.get_index(old_ticker, None, rows[0].day - timedelta(days=1))
        rows = first_rows + rows

    table.update(rows)

    last_date = table.last_row_date()
    if last_date is not None and (update_day - last_date) > _MAX_INDEX_LAG:
        ctx.warning("Index %s last value is too old - %s", ticker, last_date)
