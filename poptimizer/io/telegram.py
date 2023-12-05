import logging
from typing import Final

import aiohttp

from poptimizer.core import errors

_TELEGRAM_MAX_MSG_SIZE: Final = 4096


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

    async def send(
        self,
        component: str,
        attempt: int,
        msg: str,
    ) -> None:
        """https://core.telegram.org/bots/api#sendmessage."""
        msg = f"<b>{component}</b>\n<i>Attempt - {attempt}</i>\n\n{msg}"
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
        async with self._http_client.post(self._api_url, json=json) as resp:
            if not resp.ok:
                json = await resp.json()
                msg = json.get("description")

                self._logger.warning("can't send Telegram message - %s", msg)
