import asyncio
import logging
import sys
import time
import types
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from copy import copy
from datetime import timedelta
from email.message import EmailMessage
from typing import Final, Literal, cast

import aiosmtplib
from aiogram import loggers
from aiogram.exceptions import AiogramError

_TELEGRAM_LOGGER_NAME: Final = "Telegram"
_TELEGRAM_MAX_RPS: Final = 1

_GMAIL_LOGGER_NAME: Final = "Gmail"
_GMAIL_HOST: Final = "smtp.gmail.com"
_GMAIL_PORT: Final = 465
_GMAIL_FLUSH_DELAY: Final = timedelta(minutes=3)
_GMAIL_SUBJECT: Final = "POptimizer"

_IGNORE_LOGGER_NAMES: Final = (_TELEGRAM_LOGGER_NAME, _GMAIL_LOGGER_NAME, loggers.dispatcher.name)

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
        return record.name not in _IGNORE_LOGGER_NAMES

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


class _GmailHandler(logging.Handler):
    def __init__(
        self,
        tg: asyncio.TaskGroup,
        login: str,
        password: str,
    ) -> None:
        super().__init__(logging.WARNING)
        self._tg = tg
        self._login = login
        self._password = password
        self._buffer: list[str] = []
        self._buffer_lock = asyncio.Lock()
        self._flush_scheduled = False
        self._lgr = logging.getLogger(name=_GMAIL_LOGGER_NAME)

    def filter(self, record: logging.LogRecord) -> bool:
        return record.name not in _IGNORE_LOGGER_NAMES

    def emit(self, record: logging.LogRecord) -> None:
        self._tg.create_task(self._emit(record.getMessage()))

    async def _emit(self, msg: str) -> None:
        async with self._buffer_lock:
            self._buffer.append(msg)

            if not self._flush_scheduled:
                self._flush_scheduled = True
                self._tg.create_task(self._scheduled_flush())

    async def _scheduled_flush(self) -> None:
        await asyncio.sleep(_GMAIL_FLUSH_DELAY.total_seconds())
        await self._send_buffer()

    async def _send_buffer(self) -> None:
        async with self._buffer_lock:
            self._flush_scheduled = False

            try:
                await aiosmtplib.send(
                    self._build_msg(),
                    hostname=_GMAIL_HOST,
                    port=_GMAIL_PORT,
                    use_tls=True,
                    username=self._login,
                    password=self._password,
                )
            except aiosmtplib.SMTPException as err:
                self._lgr.warning("can't send email - %s", err)

    def _build_msg(self) -> EmailMessage:
        messages = "\n".join(self._buffer)
        self._buffer.clear()

        msg = EmailMessage()
        msg["Subject"] = _GMAIL_SUBJECT
        msg["From"] = self._login
        msg["To"] = self._login
        msg.set_content(messages)

        return msg


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
    gmail_login: str | None = None,
    gmail_password: str = "",
    send_fn: Callable[[str], Awaitable[None]] | None = None,
) -> AsyncIterator[logging.Logger]:
    color_handler = logging.StreamHandler(sys.stdout)
    color_handler.setFormatter(_ColorFormatter())
    handlers: list[logging.Handler] = [color_handler]

    tg = asyncio.TaskGroup()

    if send_fn is not None:
        handlers.append(_TelegramHandler(tg, send_fn))

    if gmail_login and gmail_password:
        handlers.append(_GmailHandler(tg, gmail_login, gmail_password))

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
