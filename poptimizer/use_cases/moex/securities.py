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

_ETF_BOARDS: Final = "TQTF"

_MARKETS_BOARDS: Final = (
    ("shares", "TQBR"),
    ("shares", _ETF_BOARDS),
)

_COLUMNS: Final = (
    "SECID",
    "LOTSIZE",
    "ISIN",
    "BOARDID",
    "SECTYPE",
    "INSTRID",
)


class _SectorRow(BaseModel):
    ticker: domain.Ticker
    till: domain.Day


type _Cache = dict[domain.Ticker, tuple[securities.Sector, domain.Day]]


class SecuritiesHandler:
    def __init__(self, http_client: aiohttp.ClientSession) -> None:
        self._http_client = http_client

    async def __call__(self, ctx: handler.Ctx, msg: handler.NewDataPublished) -> handler.SecuritiesUpdated:
        table = await ctx.get_for_update(securities.Securities)

        try:
            sector_cache, rows = await self._get_sector_cash_rows()
        except (TimeoutError, aiohttp.ClientError) as err:
            raise errors.UseCasesError("sector index MOEX ISS error") from err

        for row in rows:
            if row.board == _ETF_BOARDS:
                row.sector = securities.Sector.ETF

                continue

            row.sector, _ = sector_cache.get(row.ticker, (securities.Sector.OTHER, consts.START_DAY))

        table.update(msg.day, rows)

        return handler.SecuritiesUpdated(day=msg.day)

    async def _get_sector_cash_rows(
        self,
    ) -> tuple[_Cache, list[securities.Row]]:
        async with asyncio.TaskGroup() as tg:
            sector_cache = tg.create_task(self._prepare_sector_cache())
            rows = tg.create_task(self._download_rows())

        return await sector_cache, await rows

    async def _prepare_sector_cache(self) -> _Cache:
        cache: _Cache = {}

        async with asyncio.TaskGroup() as tg:
            for sector in securities.Sector:
                if sector.is_index():
                    tg.create_task(self._update_sector_cache(cache, sector))

        return cache

    async def _update_sector_cache(
        self,
        cache: _Cache,
        sector: securities.Sector,
    ) -> None:
        json = await aiomoex.get_index_tickers(self._http_client, sector)

        try:
            tickers = TypeAdapter(list[_SectorRow]).validate_python(json)
        except ValueError as err:
            raise errors.UseCasesError("invalid sector index data") from err

        if not tickers:
            raise errors.UseCasesError(f"no securities in sector {sector.name} index")

        for ticker in tickers:
            _, day = cache.get(ticker.ticker, (securities.Sector.OTHER, consts.START_DAY))

            if ticker.till > day:
                cache[ticker.ticker] = (sector, ticker.till)

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
