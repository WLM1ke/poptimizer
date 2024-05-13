import asyncio
import logging
from types import TracebackType
from typing import Self

from poptimizer.adapter import telegram


class Service:
    def __init__(self, logger: logging.Logger, telegram_client: telegram.Client) -> None:
        self._telegram_client = telegram_client
        self._logger = logger
        self._tg = asyncio.TaskGroup()

    async def __aenter__(self) -> Self:
        await self._tg.__aenter__()

        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        await self._tg.__aexit__(exc_type, exc_value, traceback)

    def info(self, msg: str) -> None:
        self._logger.info(msg)

    def warn(self, msg: str) -> None:
        self._logger.warning(msg)
        self._tg.create_task(self._telegram_client(msg))
