from typing import Final

import aiohttp

from poptimizer.core import errors

_TELEGRAM_MAX_MSG_SIZE: Final = 4096


class Client:
    def __init__(
        self,
        client: aiohttp.ClientSession,
        token: str,
        chat_id: str,
    ) -> None:
        self._client = client

        self._api_url = f"https://api.telegram.org/bot{token}/SendMessage"
        self._chat_id = chat_id

    async def send(self, text: str) -> None:
        """https://core.telegram.org/bots/api#sendmessage."""
        json = {
            "chat_id": self._chat_id,
            "parse_mode": "HTML",
            "text": text[:_TELEGRAM_MAX_MSG_SIZE],
        }

        async with self._client.post(self._api_url, json=json) as resp:
            if not resp.ok:
                raise errors.AdaptersError(await resp.json())
