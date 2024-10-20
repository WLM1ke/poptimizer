import asyncio
import itertools
from typing import Any, Final

import aiohttp
import aiomoex
from pydantic import TypeAdapter

from poptimizer.domain import consts
from poptimizer.domain.entity_ import entity
from poptimizer.domain.entity_.data import securities
from poptimizer.domain.service import domain_service

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


class SecuritiesUpdateService:
    def __init__(self, http_client: aiohttp.ClientSession) -> None:
        self._http_client = http_client

    async def __call__(self, ctx: domain_service.Ctx, update_day: entity.Day) -> None:
        table = await ctx.get_for_update(securities.Securities)

        rows = await self._download()

        table.update(update_day, rows)

    async def _download(self) -> list[securities.Row]:
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
            raise consts.DomainError("invalid securities data") from err
