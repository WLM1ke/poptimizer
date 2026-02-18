import asyncio
from typing import Final, Protocol

from poptimizer.actors.data.moex.models import securities
from poptimizer.core import actors, consts, domain, errors

_MARKET: Final = "shares"
_ETF_BOARDS: Final = "TQTF"
_SHARES_BOARDS: Final = "TQBR"

type _Cache = dict[domain.Ticker, tuple[securities.Sector, domain.Day]]


class MOEXClient(Protocol):
    async def get_board_securities(self, market: str, board: str) -> list[securities.Security]: ...

    async def get_index_tickers(self, index: securities.SectorIndex) -> list[securities.SectorIndexRow]: ...

    async def get_etf_desc(self) -> list[securities.ETFRow]: ...


async def update(ctx: actors.CoreCtx, moex_client: MOEXClient) -> list[securities.Security]:
    async with asyncio.TaskGroup() as tg:
        etf_task = tg.create_task(_get_etf(moex_client))
        shares_task = tg.create_task(_get_shares(moex_client))

        table = await ctx.get_for_update(securities.Securities)
        table.update(await etf_task + await shares_task)

    return table.df


async def _get_etf(moex_client: MOEXClient) -> list[securities.Security]:
    cache = {desc.ticker: desc.sector for desc in await moex_client.get_etf_desc()}
    rows = await moex_client.get_board_securities(_MARKET, _ETF_BOARDS)

    for row in rows:
        row.sector = cache.get(row.ticker, securities.OtherETF)

    return rows


async def _get_shares(moex_client: MOEXClient) -> list[securities.Security]:
    cache: _Cache = {}

    async with asyncio.TaskGroup() as tg:
        rows_task = tg.create_task(moex_client.get_board_securities(_MARKET, _SHARES_BOARDS))

        for sector in securities.SectorIndex:
            tg.create_task(_update_shares_sector_cache(moex_client, cache, sector))

    rows = await rows_task

    for row in rows:
        row.sector, _ = cache.get(row.ticker, (securities.OtherShare, consts.START_DAY))

    return rows


async def _update_shares_sector_cache(
    moex_client: MOEXClient,
    cache: _Cache,
    index: securities.SectorIndex,
) -> None:
    tickers = await moex_client.get_index_tickers(index)

    if not tickers:
        raise errors.UseCasesError(f"no securities in {index.name} index")

    sector = securities.Sector(index.name)

    for ticker in tickers:
        _, day = cache.get(ticker.ticker, (securities.OtherShare, consts.START_DAY))

        if ticker.till > day:
            cache[ticker.ticker] = (sector, ticker.till)
