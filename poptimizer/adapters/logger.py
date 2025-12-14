import asyncio
import logging
import sys
import time
import types
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from copy import copy
from typing import Final, Literal, cast

import aiohttp

_TELEGRAM_LOGGER_NAME: Final = "_telegram"
_TELEGRAM_MAX_MSG_SIZE: Final = 4096
_TELEGRAM_MAX_RPS: Final = 1

_LOGGER_NAME_SIZE: Final = 11


class _TelegramHandler(logging.Handler):
    def __init__(
        self,
        tg: asyncio.TaskGroup,
        http_client: aiohttp.ClientSession,
        token: str,
        chat_id: int,
    ) -> None:
        super().__init__(logging.WARNING)
        self._tg = tg
        self._http_client = http_client
        self._api_url = f"https://api.telegram.org/bot{token}/SendMessage"
        self._chat_id = chat_id
        self._next_send = time.monotonic()
        self._lgr = logging.getLogger(name=_TELEGRAM_LOGGER_NAME)

    def filter(self, record: logging.LogRecord) -> bool:
        return record.name != _TELEGRAM_LOGGER_NAME

    def emit(self, record: logging.LogRecord) -> None:
        self._tg.create_task(self._emit(record.getMessage()))

    async def _emit(self, msg: str) -> None:
        """https://core.telegram.org/bots/api#sendmessage."""
        json = {
            "chat_id": self._chat_id,
            "parse_mode": "HTML",
            "text": msg[:_TELEGRAM_MAX_MSG_SIZE],
        }

        try:
            await self._send(json)
        except (TimeoutError, aiohttp.ClientError) as err:
            self._lgr.warning("can't send Telegram message - %s", err)

    async def _send(self, json: dict[str, str | int]) -> None:
        await self._wait_to_send()

        async with self._http_client.post(self._api_url, json=json) as resp:
            if not resp.ok:
                json = await resp.json()
                msg = json.get("description")

                self._lgr.warning("can't send Telegram message - %s", msg)

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
    http_client: aiohttp.ClientSession | None = None,
    token: str = "",
    chat_id: int = 0,
) -> AsyncIterator[logging.Logger]:
    color_handler = logging.StreamHandler(sys.stdout)
    color_handler.setFormatter(_ColorFormatter())
    handlers: list[logging.Handler] = [color_handler]

    tg = asyncio.TaskGroup()

    if http_client is not None and token != "" and chat_id != 0:
        handlers.append(
            _TelegramHandler(
                tg,
                http_client,
                token,
                chat_id,
            )
        )

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
