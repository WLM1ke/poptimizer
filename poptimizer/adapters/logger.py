import asyncio
import logging
import sys
import time
import types
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from copy import copy
from typing import Final, Literal, cast

from aiogram.exceptions import AiogramError

_TELEGRAM_LOGGER_NAME: Final = "_telegram"
_TELEGRAM_MAX_RPS: Final = 1

_LOGGER_NAME_SIZE: Final = 11


class _TelegramHandler(logging.Handler):
    def __init__(
        self,
        tg: asyncio.TaskGroup,
        send_fn: Callable[[str], Awaitable[None]],
    ) -> None:
        super().__init__(logging.WARNING)
        self._tg = tg
        self._send_fn = send_fn
        self._next_send = time.monotonic()
        self._lgr = logging.getLogger(name=_TELEGRAM_LOGGER_NAME)

    def filter(self, record: logging.LogRecord) -> bool:
        return record.name != _TELEGRAM_LOGGER_NAME

    def emit(self, record: logging.LogRecord) -> None:
        self._tg.create_task(self._emit(record.getMessage()))

    async def _emit(self, msg: str) -> None:
        await self._wait_to_send()

        try:
            await self._send_fn(msg)
        except (TimeoutError, AiogramError) as err:
            self._lgr.warning("can't send Telegram message - %s", err)

    async def _wait_to_send(self) -> None:
        cur = time.monotonic()
        self._next_send = max(cur, self._next_send + 1.0 / _TELEGRAM_MAX_RPS)
        await asyncio.sleep(self._next_send - cur)


class _ColorFormatter(logging.Formatter):
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
        fmt: str = "{asctime} {levelname} {message}",
        datefmt: str = "%Y-%m-%d %H:%M:%S",
        style: Literal["%", "{", "$"] = "{",
    ) -> None:
        super().__init__(fmt=fmt, datefmt=datefmt, style=style)

    def formatMessage(self, record: logging.LogRecord) -> str:  # noqa: N802
        record = copy(record)
        record.levelname = self.levels[record.levelno]
        record.name = f"{record.name}:".ljust(_LOGGER_NAME_SIZE)

        return super().formatMessage(record)


@asynccontextmanager
async def init(
    send_fn: Callable[[str], Awaitable[None]] | None = None,
) -> AsyncIterator[logging.Logger]:
    color_handler = logging.StreamHandler(sys.stdout)
    color_handler.setFormatter(_ColorFormatter())
    handlers: list[logging.Handler] = [color_handler]

    tg = asyncio.TaskGroup()

    if send_fn is not None:
        handlers.append(_TelegramHandler(tg, send_fn))

    logging.basicConfig(
        level=logging.INFO,
        handlers=handlers,
    )
    logging.getLogger("pymongo").setLevel(logging.CRITICAL)

    async with tg:
        yield logging.getLogger()


def get_root_error(exc: Exception) -> Exception:
    while isinstance(exc, ExceptionGroup):
        exc = cast("Exception", exc.exceptions[0])

    return exc
