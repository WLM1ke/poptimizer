import logging
from typing import Final

import aiogram
from aiogram.filters.command import Command, CommandStart
from aiogram.types import BotCommand, Message

from poptimizer.controllers.bus import msg
from poptimizer.domain.portfolio import portfolio
from poptimizer.use_cases import handler
from poptimizer.views import utils

_PORTFOLIO_VALUE_CMD: Final = BotCommand(command="value", description="Portfolio value")


class Dispatcher(aiogram.Dispatcher):
    def __init__(self, chat_id: int, bus: msg.Bus) -> None:
        super().__init__()
        self._lgr = logging.getLogger()
        self._chat_id = chat_id

        self.message(
            aiogram.F.from_user.id != self._chat_id,
        )(self._not_owner)

        self.message(CommandStart())(self._cmd_start)

        self.message(
            Command(_PORTFOLIO_VALUE_CMD.command),
        )(bus.wrap(self._cmd_portfolio_value))

    async def _not_owner(self, message: Message) -> None:
        await message.answer(
            "You are not owner\n\nCreate your own [POptimizer](https://github.com/WLM1ke/poptimizer) bot",
            parse_mode="MarkdownV2",
        )

    def bot_commands(self) -> list[BotCommand]:
        return [
            _PORTFOLIO_VALUE_CMD,
        ]

    async def _cmd_start(self, message: Message) -> None:
        await message.answer("Welcome to POptimizer bot")

    async def _cmd_portfolio_value(self, ctx: handler.Ctx, message: Message) -> None:
        port = await ctx.get(portfolio.Portfolio)

        await message.answer(f"{utils.format_float(port.value(), 0)} ₽")
