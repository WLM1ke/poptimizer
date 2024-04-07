import asyncio
import logging
import time
from types import TracebackType
from typing import Final, Self

import aiohttp

from poptimizer.core import errors

_TELEGRAM_MAX_MSG_SIZE: Final = 4096
_TELEGRAM_MAX_RPS: Final = 1


class Logger:
    def __init__(
        self,
        logger: logging.Logger,
        http_client: aiohttp.ClientSession,
        token: str,
        chat_id: str,
    ) -> None:
        self._logger = logger
        self._http_client = http_client
        self._api_url = f"https://api.telegram.org/bot{token}/SendMessage"
        self._chat_id = chat_id
        self._next_send = time.monotonic()
        self._telegram_tasks = asyncio.TaskGroup()

    async def __aenter__(self) -> Self:
        await self._telegram_tasks.__aenter__()

        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        await self._telegram_tasks.__aexit__(exc_type, exc_value, traceback)

    def info(self, msg: str) -> None:
        self._logger.info(msg)

    def warning(self, msg: str) -> None:
        self._logger.warning(msg)
        self._telegram_tasks.create_task(self._warn(msg))

    async def _warn(self, msg: str) -> None:
        """https://core.telegram.org/bots/api#sendmessage."""
        json = {
            "chat_id": self._chat_id,
            "parse_mode": "HTML",
            "text": msg[:_TELEGRAM_MAX_MSG_SIZE],
        }
        try:
            await self._send(json)
        except errors.InputOutputError as err:
            self._logger.warning("can't send Telegram message - %s", err)

    async def _send(self, json: dict[str, str]) -> None:
        await self._wait_to_send()

        async with self._http_client.post(self._api_url, json=json) as resp:
            if not resp.ok:
                json = await resp.json()
                msg = json.get("description")

                self._logger.warning("can't send Telegram message - %s", msg)

    async def _wait_to_send(self) -> None:
        cur = time.monotonic()
        self._next_send = max(cur, self._next_send + 1.0 / _TELEGRAM_MAX_RPS)
        await asyncio.sleep(self._next_send - cur)
