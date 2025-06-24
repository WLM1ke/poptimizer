import asyncio
import itertools
from typing import Any, Final

import aiohttp
import aiomoex
from pydantic import BaseModel, Field, TypeAdapter

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

_ETF_URL: Final = "https://rusetfs.com/api/v1/screener"


class _IndexSectorRow(BaseModel):
    ticker: domain.Ticker
    till: domain.Day


class _NamedAttr(BaseModel):
    name: str


class _ETFSectorRow(BaseModel):
    ticker: domain.Ticker
    sub_class: _NamedAttr = Field(alias="assetSubClass")
    currency: _NamedAttr = Field(alias="currency")

    @property
    def sector(self) -> domain.Sector:
        return domain.Sector(f"{self.sub_class.name} - {self.currency.name}")


type _Cache = dict[domain.Ticker, tuple[domain.Sector, domain.Day]]


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
            default_sector = domain.OtherShare
            if row.board == _ETF_BOARDS:
                default_sector = domain.OtherETF

            row.sector, _ = sector_cache.get(row.ticker, (default_sector, consts.START_DAY))

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
            for sector in securities.SectorIndex:
                tg.create_task(self._update_shares_sector_cache(cache, sector))

            try:
                await self._update_etf_sector_cache(cache)
            except (TimeoutError, aiohttp.ClientError) as err:
                raise errors.UseCasesError("can't download etf description") from err

        return cache

    async def _update_etf_sector_cache(self, cache: _Cache) -> None:
        async with self._http_client.get(_ETF_URL) as resp:
            if not resp.ok:
                raise errors.UseCasesError(f"bad etf description respond {resp.reason}")

            try:
                etf_desc = TypeAdapter(list[_ETFSectorRow]).validate_python(await resp.json())
            except ValueError as err:
                raise errors.UseCasesError("invalid etf description data") from err

        for desc in etf_desc:
            cache[desc.ticker] = (desc.sector, consts.START_DAY)

    async def _update_shares_sector_cache(
        self,
        cache: _Cache,
        index: securities.SectorIndex,
    ) -> None:
        try:
            json = await aiomoex.get_index_tickers(self._http_client, index)
        except (TimeoutError, aiohttp.ClientError) as err:
            raise errors.UseCasesError(f"can't download {index.name} data") from err

        try:
            tickers = TypeAdapter(list[_IndexSectorRow]).validate_python(json)
        except ValueError as err:
            raise errors.UseCasesError(f"invalid {index.name} data") from err

        if not tickers:
            raise errors.UseCasesError(f"no securities in {index.name} index")

        sector = domain.Sector(index.name)

        for ticker in tickers:
            _, day = cache.get(ticker.ticker, (domain.OtherShare, consts.START_DAY))

            if ticker.till > day:
                cache[ticker.ticker] = (sector, ticker.till)

    async def _download_rows(self) -> list[securities.Row]:
        tasks: list[asyncio.Task[list[dict[str, Any]]]] = []

        async with asyncio.TaskGroup() as tg:
            for market, board in _MARKETS_BOARDS:
                task = tg.create_task(self._download_board_rows(market, board))
                tasks.append(task)

        json = list(itertools.chain.from_iterable([await task for task in tasks]))

        try:
            return TypeAdapter(list[securities.Row]).validate_python(json)
        except ValueError as err:
            raise errors.UseCasesError("invalid securities data") from err

    async def _download_board_rows(self, market: str, board: str) -> list[dict[str, Any]]:
        try:
            return await aiomoex.get_board_securities(
                self._http_client,
                market=market,
                board=board,
                columns=_COLUMNS,
            )
        except (TimeoutError, aiohttp.ClientError) as err:
            raise errors.UseCasesError(f"can't download {market} {board} data") from err
