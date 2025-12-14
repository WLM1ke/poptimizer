import logging

import aiogram
from aiogram.filters import Command
from aiogram.types import Message

from poptimizer.controllers.bus import msg


class Dispatcher(aiogram.Dispatcher):
    def __init__(self, bus: msg.Bus) -> None:
        super().__init__()
        self._lgr = logging.getLogger()
        self._bus = bus
        self.message(Command("start"))(self._start_handler)

    async def _start_handler(self, message: Message) -> None:
        await message.answer("Welcome to POptimizer Telegram bot!")
