import asyncio
import logging

import aiogram
import aiohttp

from poptimizer.controllers.bus import msg
from poptimizer.views.tg import tg


class Bot:
    def __init__(self, token: str, bus: msg.Bus, http_client: aiohttp.ClientSession) -> None:
        self._lgr = logging.getLogger()
        match token:
            case "":
                self._bot = None
            case _:
                self._bot = aiogram.Bot(token=token, client_session=http_client)

        self._dp = tg.Dispatcher(bus)

    async def run(self) -> None:
        if self._bot is None:
            return

        self._lgr.info("Starting Telegram bot...")

        try:
            await self._dp.start_polling(  # pyright: ignore[reportUnknownMemberType]
                self._bot,
                handle_signals=False,
            )
        except asyncio.CancelledError:
            await self._bot.session.close()
            self._lgr.info("Telegram bot shutdown finished")
