import asyncio
import logging
from datetime import date, timedelta
from typing import TYPE_CHECKING, Final

import aiomoex
from pydantic import TypeAdapter

from poptimizer.domain import domain
from poptimizer.domain.moex import index
from poptimizer.use_cases import handler

if TYPE_CHECKING:
    import aiohttp

_MAX_INDEX_LAG: Final = timedelta(days=7)


class IndexesHandler:
    def __init__(self, http_client: aiohttp.ClientSession) -> None:
        self._http_client = http_client
        self._lgr = logging.getLogger()

    async def __call__(self, ctx: handler.Ctx, msg: handler.QuotesUpdated) -> None:
        async with asyncio.TaskGroup() as tg:
            for ticker in index.INDEXES:
                tg.create_task(self._update_one(ctx, msg.day, ticker))

        ctx.publish(handler.IndexesUpdated(trading_days=msg.trading_days))

    async def _update_one(self, ctx: handler.Ctx, update_day: domain.Day, ticker: domain.UID) -> None:
        table = await ctx.get_for_update(index.Index, ticker)

        start_day = table.last_row_date()
        rows = await self._download(ticker, start_day, update_day)

        if start_day is None and (old_ticker := index.INDEXES[ticker]) is not None:
            first_rows = await self._download(old_ticker, None, rows[0].day - timedelta(days=1))
            rows = first_rows + rows

        table.update(update_day, rows)

        last_date = table.last_row_date()
        if last_date is not None and (update_day - last_date) > _MAX_INDEX_LAG:
            self._lgr.warning("Index %s last value is too old: %s", ticker, last_date)

    async def _download(
        self,
        ticker: str,
        start_day: date | None,
        update_day: date,
    ) -> list[index.Row]:
        async with handler.wrap_http_err(f"{ticker} MOEX ISS error"):
            json = await aiomoex.get_market_candles(
                session=self._http_client,
                start=start_day and str(start_day),
                end=str(update_day),
                interval=24,
                security=ticker,
                market="index",
                engine="stock",
            )

        with handler.wrap_validation_err(f"invalid {ticker} data"):
            return _deduplicate_rows(TypeAdapter(list[index.Row]).validate_python(json))


def _deduplicate_rows(rows: list[index.Row]) -> list[index.Row]:
    prev_row: index.Row | None = None
    rows_deduplicated: list[index.Row] = []

    for row in rows:
        if row == prev_row:
            continue

        rows_deduplicated.append(row)
        prev_row = row

    return rows_deduplicated
