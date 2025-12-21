import asyncio
import logging
from types import TracebackType
from typing import Final, Self

import aiogram
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.utils import formatting

from poptimizer.adapters import mongo
from poptimizer.controllers.bus import msg
from poptimizer.views.tg import tg

_TELEGRAM_MAX_MSG_SIZE: Final = 4096


class Bot:
    def __init__(self, token: str, chat_id: int) -> None:
        self._chat_id = chat_id
        match token:
            case "":
                self._bot = None
            case _:
                self._bot = aiogram.Bot(
                    token=token,
                    default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN_V2),
                )

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if self._bot is not None:
            await self._bot.session.close()

    async def send_message(self, text: str) -> None:
        if self._bot is None:
            return

        msg = formatting.Text(text).as_markdown()[:_TELEGRAM_MAX_MSG_SIZE]

        await self._bot.send_message(self._chat_id, msg)

    async def run(self, lgr: logging.Logger, mong_db: mongo.MongoDatabase, bus: msg.Bus) -> None:
        if self._bot is None:
            return

        lgr.info("Starting Telegram bot...")

        dp, commands = tg.dispatcher(self._chat_id, mong_db, bus)
        await self._bot.set_my_commands(commands)

        try:
            await asyncio.shield(
                dp.start_polling(  # pyright: ignore[reportUnknownMemberType]
                    self._bot,
                    handle_signals=False,
                    drop_pending_updates=True,
                )
            )
        except asyncio.CancelledError:
            await dp.stop_polling()
            lgr.info("Telegram bot shutdown finished")
