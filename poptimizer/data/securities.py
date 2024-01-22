import asyncio
import itertools
from typing import Any, Final

import aiohttp
import aiomoex
from pydantic import Field, TypeAdapter, field_validator

from poptimizer.core import domain
from poptimizer.data import data, trading_day

_SHARES_BOARD: Final = "TQBR"
_PREFERRED_TYPE: Final = "2"
_PREFERRED_SUFFIX: Final = "P"

_MARKETS_BOARDS: Final = (
    ("shares", _SHARES_BOARD),
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


class _Row(data.Row):
    ticker: domain.Ticker = Field(alias="SECID")
    lot: int = Field(alias="LOTSIZE")
    isin: str = Field(alias="ISIN")
    board: str = Field(alias="BOARDID")
    type: str = Field(alias="SECTYPE")
    instrument: str = Field(alias="INSTRID")

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
    df: list[_Row] = Field(default_factory=list[_Row])

    def update(self, update_day: domain.Day, rows: list[_Row]) -> None:
        self.timestamp = update_day

        rows.sort(key=lambda sec: sec.ticker)

        self.df = rows

    @field_validator("df")
    def _must_be_sorted_by_ticker(cls, df: list[_Row]) -> list[_Row]:
        ticker_pairs = itertools.pairwise(row.ticker for row in df)

        if not all(ticker < next_ for ticker, next_ in ticker_pairs):
            raise ValueError("tickers are not sorted")

        return df


class SecuritiesUpdated(domain.Event):
    day: domain.Day


class SecuritiesEventHandler:
    def __init__(self, http_client: aiohttp.ClientSession) -> None:
        self._http_client = http_client

    async def handle(self, ctx: domain.Ctx, event: trading_day.TradingDayEnded) -> None:
        table = await ctx.get(Securities)

        rows = await self._download()

        update_day = event.day
        table.update(update_day, rows)
        ctx.publish(SecuritiesUpdated(day=update_day))

    async def _download(self) -> list[_Row]:
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

        return TypeAdapter(list[_Row]).validate_python(json)
