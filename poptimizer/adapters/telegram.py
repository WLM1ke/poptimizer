import asyncio
import logging
import time
from typing import Final

import aiohttp

from poptimizer.core import errors

_TELEGRAM_MAX_MSG_SIZE: Final = 4096
_TELEGRAM_MAX_RPS: Final = 1


class Client:
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

    async def __call__(self, msg: str) -> None:
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


class Logger:
    def __init__(
        self,
        logger: logging.Logger,
        telegram_client: Client,
        tg: asyncio.TaskGroup,
    ) -> None:
        self._logger = logger
        self._telegram_client = telegram_client
        self._tg = tg

    def info(self, msg: str) -> None:
        self._logger.info(msg)

    def warning(self, msg: str) -> None:
        self._logger.warning(msg)
        self._tg.create_task(self._telegram_client(msg))
