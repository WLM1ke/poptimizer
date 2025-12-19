import asyncio
import logging

import aiogram
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from poptimizer.controllers.bus import msg
from poptimizer.views.tg import tg


class Bot:
    def __init__(self, token: str, chat_id: int, bus: msg.Bus) -> None:
        self._lgr = logging.getLogger()
        match token:
            case "":
                self._bot = None
            case _:
                self._bot = aiogram.Bot(
                    token=token,
                    default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN_V2),
                )

        self._dp, self._commands = tg.view(chat_id, bus)

    async def run(self) -> None:
        if self._bot is None:
            return

        self._lgr.info("Starting Telegram bot...")

        async with self._bot:
            await self._bot.set_my_commands(self._commands)

            try:
                await asyncio.shield(
                    self._dp.start_polling(  # pyright: ignore[reportUnknownMemberType]
                        self._bot,
                        handle_signals=False,
                        drop_pending_updates=True,
                    )
                )
            except asyncio.CancelledError:
                await self._dp.stop_polling()
                self._lgr.info("Telegram bot shutdown finished")
