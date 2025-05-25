import asyncio
import itertools
from typing import Any, Final

import aiohttp
import aiomoex
from pydantic import BaseModel, TypeAdapter

from poptimizer import consts, errors
from poptimizer.domain import domain
from poptimizer.domain.moex import securities
from poptimizer.use_cases import handler

_MARKETS_BOARDS: Final = (
    ("shares", "TQBR"),
    ("shares", "TQTF"),
)

_COLUMNS: Final = (
    "SECID",
    "LOTSIZE",
    "ISIN",
    "BOARDID",
    "SECTYPE",
    "INSTRID",
)


class _IndustryRow(BaseModel):
    ticker: domain.Ticker
    till: domain.Day


type _Cache = dict[domain.Ticker, tuple[securities.IndustryIndex, domain.Day]]


class SecuritiesHandler:
    def __init__(self, http_client: aiohttp.ClientSession) -> None:
        self._http_client = http_client

    async def __call__(self, ctx: handler.Ctx, msg: handler.NewDataPublished) -> handler.SecuritiesUpdated:
        table = await ctx.get_for_update(securities.Securities)

        try:
            industry_cache, rows = await self._get_industry_cash_rows()
        except (TimeoutError, aiohttp.ClientError) as err:
            raise errors.UseCasesError("industry index composition MOEX ISS error") from err

        for row in rows:
            row.industry, _ = industry_cache.get(row.ticker, (securities.IndustryIndex.UNKNOWN, consts.START_DAY))

        table.update(msg.day, rows)

        return handler.SecuritiesUpdated(day=msg.day)

    async def _get_industry_cash_rows(
        self,
    ) -> tuple[_Cache, list[securities.Row]]:
        async with asyncio.TaskGroup() as tg:
            industry_cache = tg.create_task(self._prepare_industry_cache())
            rows = tg.create_task(self._download_rows())

        return await industry_cache, await rows

    async def _prepare_industry_cache(self) -> _Cache:
        cache: _Cache = {}

        async with asyncio.TaskGroup() as tg:
            for index in securities.IndustryIndex:
                if index == securities.IndustryIndex.UNKNOWN:
                    continue

                tg.create_task(self._update_industry_cache(cache, index))

        return cache

    async def _update_industry_cache(
        self,
        cache: _Cache,
        index: securities.IndustryIndex,
    ) -> None:
        json = await aiomoex.get_index_tickers(self._http_client, index)

        try:
            tickers = TypeAdapter(list[_IndustryRow]).validate_python(json)
        except ValueError as err:
            raise errors.UseCasesError("invalid index composition data") from err

        if not tickers:
            raise errors.UseCasesError(f"no securities in industry {index.name}")

        for ticker in tickers:
            _, day = cache.get(ticker.ticker, (securities.IndustryIndex.UNKNOWN, consts.START_DAY))

            if ticker.till > day:
                cache[ticker.ticker] = (index, ticker.till)

    async def _download_rows(self) -> list[securities.Row]:
        tasks: list[asyncio.Task[list[dict[str, Any]]]] = []

        async with asyncio.TaskGroup() as tg:
            for market, board in _MARKETS_BOARDS:
                task = tg.create_task(
                    aiomoex.get_board_securities(
                        self._http_client,
                        market=market,
                        board=board,
                        columns=_COLUMNS,
                    ),
                )
                tasks.append(task)

        json = list(itertools.chain.from_iterable([await task for task in tasks]))

        try:
            return TypeAdapter(list[securities.Row]).validate_python(json)
        except ValueError as err:
            raise errors.UseCasesError("invalid securities data") from err
