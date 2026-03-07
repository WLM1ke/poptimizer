import asyncio
from enum import StrEnum, auto
from typing import Annotated, Final, NewType, Protocol

from pydantic import AfterValidator, BaseModel, Field, PositiveInt

from poptimizer.core import consts, domain, errors, fsm

_MARKET: Final = "shares"
_ETF_BOARD: Final = "TQTF"
_SHARES_BOARD: Final = "TQBR"

_PREFERRED_TYPE: Final = "2"
_PREFERRED_SUFFIX: Final = "P"


class SectorIndex(StrEnum):
    MOEXOG = auto()
    MOEXEU = auto()
    MOEXTL = auto()
    MOEXMM = auto()
    MOEXFN = auto()
    MOEXCN = auto()
    MOEXCH = auto()
    MOEXTN = auto()
    MOEXIT = auto()
    MOEXRE = auto()


Sector = NewType("Sector", str)
OtherShare: Final = Sector("Other share")
OtherETF: Final = Sector("Other ETF")


class SectorIndexRow(BaseModel):
    ticker: domain.Ticker
    till: domain.Day


class ETFAttr(BaseModel):
    name: str


class ETFRow(BaseModel):
    ticker: domain.Ticker
    sub_class: ETFAttr = Field(alias="assetSubClass")
    currency: ETFAttr = Field(alias="currency")

    @property
    def sector(self) -> Sector:
        return Sector(f"{self.sub_class.name} - {self.currency.name}")


class Row(domain.Row):
    ticker: domain.Ticker = Field(alias="SECID")
    lot: PositiveInt = Field(alias="LOTSIZE")
    isin: str = Field(alias="ISIN")
    board: str = Field(alias="BOARDID")
    type: str = Field(alias="SECTYPE")
    instrument: str = Field(alias="INSTRID")
    sector: Sector = OtherShare

    @property
    def is_share(self) -> bool:
        return self.board == _SHARES_BOARD

    @property
    def is_preferred(self) -> bool:
        return (self.type == _PREFERRED_TYPE) and self.is_share

    @property
    def ticker_base(self) -> str:
        if self.is_preferred:
            return self.ticker.removesuffix(_PREFERRED_SUFFIX)

        return self.ticker


class Securities(domain.Entity):
    df: Annotated[
        list[Row],
        AfterValidator(domain.sorted_with_ticker_field_validator),
    ] = Field(default_factory=list[Row])

    def update_df(self, rows: list[Row]) -> None:
        self.df = sorted(rows, key=lambda sec: sec.ticker)


type _Cache = dict[domain.Ticker, tuple[Sector, domain.Day]]


class Client(Protocol):
    async def get_securities(self, market: str, board: str) -> list[Row]: ...

    async def get_index_tickers(self, index: SectorIndex) -> list[SectorIndexRow]: ...

    async def get_etf_desc(self) -> list[ETFRow]: ...


async def update(ctx: fsm.Ctx, moex_client: Client) -> Securities:
    async with asyncio.TaskGroup() as tg:
        etf_task = tg.create_task(_get_etf(moex_client))
        shares_task = tg.create_task(_get_shares(moex_client))

        table = await ctx.get_for_update(Securities)
        table.update_df(await etf_task + await shares_task)

    return table


async def _get_etf(moex_client: Client) -> list[Row]:
    cache = {desc.ticker: desc.sector for desc in await moex_client.get_etf_desc()}
    rows = await moex_client.get_securities(_MARKET, _ETF_BOARD)

    for row in rows:
        row.sector = cache.get(row.ticker, OtherETF)

    return rows


async def _get_shares(moex_client: Client) -> list[Row]:
    cache: _Cache = {}

    async with asyncio.TaskGroup() as tg:
        rows_task = tg.create_task(moex_client.get_securities(_MARKET, _SHARES_BOARD))

        for sector in SectorIndex:
            tg.create_task(_update_shares_sector_cache(moex_client, cache, sector))

    rows = await rows_task

    for row in rows:
        row.sector, _ = cache.get(row.ticker, (OtherShare, consts.START_DAY))

    return rows


async def _update_shares_sector_cache(
    moex_client: Client,
    cache: _Cache,
    index: SectorIndex,
) -> None:
    tickers = await moex_client.get_index_tickers(index)

    if not tickers:
        raise errors.UseCasesError(f"no securities in {index.name} index")

    sector = Sector(index.name)

    for ticker in tickers:
        _, day = cache.get(ticker.ticker, (OtherShare, consts.START_DAY))

        if ticker.till > day:
            cache[ticker.ticker] = (sector, ticker.till)
