from typing import Protocol

from poptimizer.actors.data.cpi import models
from poptimizer.actors.data.moex.models import securities
from poptimizer.core import actors, domain


class MemoryChecker(Protocol):
    def check_memory_usage(self, ctx: actors.Ctx) -> None: ...


class MigrationClient(Protocol):
    async def migrate(self, ctx: actors.Ctx, last_version: str) -> bool: ...


class CBRClient(Protocol):
    async def download_cpi(self) -> list[models.CPIRow]: ...


class MOEXClient(Protocol):
    async def last_trading_day(self) -> domain.Day: ...

    async def get_board_securities(self, market: str, board: str) -> list[securities.Security]: ...

    async def get_index_tickers(self, index: securities.SectorIndex) -> list[securities.SectorIndexRow]: ...

    async def get_etf_desc(self) -> list[securities.ETFRow]: ...
