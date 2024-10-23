import asyncio
import itertools
from typing import Any, Final

import aiohttp
import aiomoex
from pydantic import TypeAdapter

from poptimizer import errors
from poptimizer.domain.data import securities
from poptimizer.handlers import handler

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


class SecuritiesHandler:
    def __init__(self, http_client: aiohttp.ClientSession) -> None:
        self._http_client = http_client

    async def __call__(self, ctx: handler.Ctx, msg: handler.IndexesUpdated) -> None:
        table = await ctx.get_for_update(securities.Securities)

        try:
            rows = await self._download()
        except (TimeoutError, aiohttp.ClientError) as err:
            raise errors.HandlerError("securities MOEX ISS error") from err

        table.update(msg.day, rows)
        ctx.publish(handler.SecuritiesUpdated(day=msg.day))

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
            raise errors.HandlerError("invalid securities data") from err
