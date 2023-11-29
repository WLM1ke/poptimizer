from typing import Final

import aiohttp

from poptimizer.core import domain, errors

_TELEGRAM_MAX_MSG_SIZE: Final = 4096


class ErrorHappened(domain.Event):
    handler: str
    attempt: int
    msg: str


class ErrorEventHandler:
    def __init__(
        self,
        client: aiohttp.ClientSession,
        token: str,
        chat_id: str,
    ) -> None:
        self._client = client
        self._api_url = f"https://api.telegram.org/bot{token}/SendMessage"
        self._chat_id = chat_id

    async def handle(self, ctx: domain.Ctx, event: ErrorHappened) -> None:  # noqa: ARG002
        """https://core.telegram.org/bots/api#sendmessage."""
        msg = f"<b>{event.handler}</b>\n<i>Attempt - {event.attempt}</i>\n\n{event.msg}"
        json = {
            "chat_id": self._chat_id,
            "parse_mode": "HTML",
            "text": msg[:_TELEGRAM_MAX_MSG_SIZE],
        }

        async with self._client.post(self._api_url, json=json) as resp:
            if not resp.ok:
                json = await resp.json()
                msg = json.get("description")

                raise errors.AdaptersError(msg)
