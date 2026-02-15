import asyncio
from typing import Final

from poptimizer.adapters.moex import Client
from poptimizer.core import consts, domain, errors
from poptimizer.domain.moex import securities
from poptimizer.use_cases import handler

_MARKET: Final = "shares"
_ETF_BOARDS: Final = "TQTF"
_SHARES_BOARDS: Final = "TQBR"

type _Cache = dict[domain.Ticker, tuple[securities.Sector, domain.Day]]


class SecuritiesHandler:
    def __init__(self, moex_client: Client) -> None:
        self._moex_client = moex_client

    async def __call__(self, ctx: handler.Ctx, msg: handler.NewDataPublished) -> None:

        async with asyncio.TaskGroup() as tg:
            etf_task = tg.create_task(self._get_etf())
            shares_task = tg.create_task(self._get_shares())

            table = await ctx.get_for_update(securities.Securities)
            table.update(msg.day, await etf_task + await shares_task)

    async def _get_etf(self) -> list[securities.Security]:
        cache = {desc.ticker: desc.sector for desc in await self._moex_client.get_etf_desc()}
        rows = await self._moex_client.get_board_securities(_MARKET, _ETF_BOARDS)

        for row in rows:
            row.sector = cache.get(row.ticker, securities.OtherETF)

        return rows

    async def _get_shares(self) -> list[securities.Security]:
        cache: _Cache = {}

        async with asyncio.TaskGroup() as tg:
            rows_task = tg.create_task(self._moex_client.get_board_securities(_MARKET, _SHARES_BOARDS))

            for sector in securities.SectorIndex:
                tg.create_task(self._update_shares_sector_cache(cache, sector))

        rows = await rows_task

        for row in rows:
            row.sector, _ = cache.get(row.ticker, (securities.OtherShare, consts.START_DAY))

        return rows

    async def _update_shares_sector_cache(
        self,
        cache: _Cache,
        index: securities.SectorIndex,
    ) -> None:
        tickers = await self._moex_client.get_index_tickers(index)

        if not tickers:
            raise errors.UseCasesError(f"no securities in {index.name} index")

        sector = securities.Sector(index.name)

        for ticker in tickers:
            _, day = cache.get(ticker.ticker, (securities.OtherShare, consts.START_DAY))

            if ticker.till > day:
                cache[ticker.ticker] = (sector, ticker.till)
