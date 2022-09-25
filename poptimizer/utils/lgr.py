"""Настройки логирования."""
import asyncio
import html
import logging
import sys
import types
from collections.abc import AsyncGenerator
from concurrent import futures
from contextlib import asynccontextmanager, contextmanager
from copy import copy
from typing import Final, Generator, Literal

import aiohttp

COLOR_MSG: Final = "color_msg"
_LOGGER_NAME_SIZE: Final = 11
_MAX_TELEGRAM_MSG_SIZE: Final = 4096


class ColorFormatter(logging.Formatter):
    """Цветное логирование."""

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
        """Подменяет отображение уровня логирования цветным аналогом."""
        record = copy(record)
        record.levelname = self.levels[record.levelno]

        if "aiohttp" in record.name:
            record.name = "Server"

        record.name = f"{record.name}:".ljust(_LOGGER_NAME_SIZE)

        if color_msg := getattr(record, COLOR_MSG, None):
            record.msg = color_msg
            record.message = record.getMessage()

        return super().formatMessage(record)


class AsyncTelegramHandler(logging.Handler):
    """Отправляет сообщения уровня WARNING и выше в Телеграм.

    При этом исключаются сообщения самого обработчика, чтобы не вызвать рекурсивную отправку в случае ошибки в работе.
    Использует асинхронную отправку, поэтому должен использоваться после запуска eventloop.
    """

    def __init__(self, session: aiohttp.ClientSession, token: str, chat_id: str) -> None:
        super().__init__(level=logging.WARNING)

        formatter = logging.Formatter(
            fmt="<strong>{name}</strong>\n{message}",
            style="{",
        )
        self.setFormatter(formatter)
        self.addFilter(lambda record: record.name != "Telegram")

        self._logger = logging.getLogger("Telegram")
        self._session = session
        self._url = f"https://api.telegram.org/bot{token}/SendMessage"
        self._chat_id = chat_id

        self._loop = asyncio.get_running_loop()
        self._futures: set[futures.Future[None]] = set()

    def emit(self, record: logging.LogRecord) -> None:
        """Выполняет асинхронную отправку сообщения в Телеграм - потокобезопасен."""
        future = asyncio.run_coroutine_threadsafe(self._send(record), self._loop)
        self._futures.add(future)
        future.add_done_callback(self._callback)

    async def force_send(self) -> None:
        """Завершает посылку сообщений в телеграм - важно для посылки сообщения о падении приложения."""
        with self._lock():
            aws = [asyncio.to_thread(fut.result) for fut in frozenset(self._futures)]

        if aws:
            await asyncio.wait(aws)

    async def _send(self, record: logging.LogRecord) -> None:
        """https://core.telegram.org/bots/api#sendmessage."""
        record = copy(record)
        record.msg = html.escape(record.msg)

        json = {
            "chat_id": self._chat_id,
            "parse_mode": "HTML",
            "text": self.format(record)[:_MAX_TELEGRAM_MSG_SIZE],
        }

        async with self._session.post(self._url, json=json) as resp:
            if not resp.ok:
                err_desc = await resp.json()
                self._logger.warning(f"can't send {err_desc}")

    @contextmanager
    def _lock(self) -> Generator[None, None, None]:
        self.acquire()
        try:
            yield
        finally:
            self.release()

    def _callback(self, future: futures.Future[None]) -> None:
        with self._lock():
            self._futures.discard(future)


@asynccontextmanager
async def config(
    session: aiohttp.ClientSession,
    token: str,
    chat_id: str,
    level: int | str = logging.INFO,
) -> AsyncGenerator[None, None]:
    """Настраивает логирование в stdout, а для уровней WARNING и выше в Телеграм."""
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(ColorFormatter())

    telegram_handler = AsyncTelegramHandler(session, token, chat_id)

    logging.basicConfig(
        level=level,
        handlers=[stream_handler, telegram_handler],
    )

    try:
        yield
    finally:
        await telegram_handler.force_send()
