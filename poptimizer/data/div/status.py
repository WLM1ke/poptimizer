import itertools
from collections.abc import AsyncIterable, Iterable
from typing import Annotated, Protocol

from pydantic import AfterValidator, Field

from poptimizer.core import domain, fsm
from poptimizer.data.div import raw
from poptimizer.data.moex import securities
from poptimizer.data.portfolio import portfolio


class Row(domain.Row):
    ticker: domain.Ticker
    ticker_base: str
    preferred: bool
    day: domain.Day


def _must_be_sorted_by_ticker_and_day(df: list[Row]) -> list[Row]:
    ticker_date_pairs = itertools.pairwise((row.ticker, row.day) for row in df)

    if not all(ticker_date <= next_ for ticker_date, next_ in ticker_date_pairs):
        raise ValueError("ticker and dates are not sorted")

    return df


class DivStatus(domain.Entity):
    df: Annotated[
        list[Row],
        AfterValidator(_must_be_sorted_by_ticker_and_day),
    ] = Field(default_factory=list[Row])

    def update(self, rows: list[Row]) -> None:
        rows.sort(key=lambda status: (status.ticker, status.day))
        self.df = rows

    def filter(self, raw_table: raw.DivRaw) -> None:
        self.df = [
            status
            for status in self.df
            if not (status.ticker == domain.Ticker(raw_table.uid) and raw_table.has_day(status.day))
        ]


class Client(Protocol):
    async def get_status(self) -> Iterable[tuple[domain.Ticker, domain.Day]]: ...


async def update(ctx: fsm.CoreCtx, status_client: Client) -> None:
    table = await ctx.get_for_update(DivStatus)

    status = await status_client.get_status()

    table.update([row async for row in _status_gen(ctx, status)])


async def _status_gen(
    ctx: fsm.CoreCtx,
    raw_rows: Iterable[tuple[domain.Ticker, domain.Day]],
) -> AsyncIterable[Row]:
    sec = await ctx.get(securities.Securities)
    port = await ctx.get(portfolio.Portfolio)

    sec_cache = {row.ticker: row for row in sec.df if port.find_position(row.ticker)[1] is not None}

    for ticker, day in raw_rows:
        if not (sec_desc := sec_cache.get(ticker)):
            continue

        raw_div = await ctx.get(raw.DivRaw, domain.UID(ticker))

        if raw_div.has_day(day):
            continue

        ctx.warning("%s missed dividend at %s", ticker, day)

        yield Row(
            ticker=ticker,
            ticker_base=sec_desc.ticker_base,
            preferred=sec_desc.is_preferred,
            day=day,
        )
