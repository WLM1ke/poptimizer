import asyncio
import logging
import sys
import types
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from copy import copy
from typing import Final, Literal

import aiohttp

from poptimizer.core import errors
from poptimizer.io import telegram

_TELEGRAM_LOGGER_NAME: Final = "Telegram"
_LOGGER_NAME_SIZE: Final = 11


class _TelegramFormatter(logging.Formatter):
    def __init__(
        self,
        fmt: str = "\n<strong>{name}</strong>{message}",
        datefmt: str = "%Y-%m-%d %H:%M:%S",
        style: Literal["%", "{", "$"] = "{",
    ) -> None:
        super().__init__(fmt=fmt, datefmt=datefmt, style=style)

    def formatMessage(self, record: logging.LogRecord) -> str:  # noqa: N802
        """Накладывает ограничение на размер сообщения."""
        return super().formatMessage(record)


class _TelegramFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return record.name != _TELEGRAM_LOGGER_NAME


class _TelegramHandler(logging.Handler):
    def __init__(
        self,
        telegram: telegram.Client,
        level: int | str,
        task_group: asyncio.TaskGroup,
    ) -> None:
        super().__init__(level)
        self.setFormatter(_TelegramFormatter())
        self.addFilter(_TelegramFilter())

        self._logger = logging.getLogger(_TELEGRAM_LOGGER_NAME)
        self._telegram = telegram

        self._loop = asyncio.get_running_loop()
        self._tg = task_group

    def emit(self, record: logging.LogRecord) -> None:
        asyncio.run_coroutine_threadsafe(self._create_send_task(record), loop=self._loop)

    async def _create_send_task(self, record: logging.LogRecord) -> None:
        self._tg.create_task(self._send(record))

    async def _send(self, record: logging.LogRecord) -> None:
        try:
            await self._telegram.send(self.format(record))
        except errors.AdaptersError as err:
            self._logger.warning(err)


class _ColorFormatter(logging.Formatter):
    """Форматирует сообщения с цветным наименованием уровня."""

    levels: Final = types.MappingProxyType(
        {
            logging.DEBUG: "\033[90mDBG\033[0m",
            logging.INFO: "\033[34mINF\033[0m",
            logging.WARNING: "\033[31mWRN\033[0m",
            logging.ERROR: "\033[1;31mERR\033[0m",
            logging.CRITICAL: "\033[1;91mCRT\033[0m",
        },
    )

    def __init__(
        self,
        fmt: str = "{asctime} {levelname} {name} {message}",
        datefmt: str = "%Y-%m-%d %H:%M:%S",
        style: Literal["%", "{", "$"] = "{",
    ) -> None:
        super().__init__(fmt=fmt, datefmt=datefmt, style=style)

    def formatMessage(self, record: logging.LogRecord) -> str:  # noqa: N802
        record = copy(record)
        record.levelname = self.levels[record.levelno]

        if "aiohttp" in record.name:
            record.name = "Server"

        record.name = f"{record.name}:".ljust(_LOGGER_NAME_SIZE)

        return super().formatMessage(record)


@asynccontextmanager
async def init(
    client: aiohttp.ClientSession,
    level: int | str,
    telegram_level: int | str,
    telegram_token: str,
    telegram_chat_id: str,
) -> AsyncGenerator[None, None]:
    """Настраивает логирование в stdout."""
    async with asyncio.TaskGroup() as tg:
        color_handler = logging.StreamHandler(sys.stdout)
        color_handler.setFormatter(_ColorFormatter())

        telegram_handler = _TelegramHandler(
            telegram.Client(
                client,
                telegram_token,
                telegram_chat_id,
            ),
            telegram_level,
            tg,
        )

        logging.basicConfig(
            level=level,
            handlers=[
                color_handler,
                telegram_handler,
            ],
        )

        yield
