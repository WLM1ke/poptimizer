import itertools
import logging
from typing import Final

import aiogram
from aiogram.filters.command import CommandStart
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, Message, ReplyKeyboardMarkup
from aiogram.utils import formatting

from poptimizer.controllers.bus import msg
from poptimizer.domain.portfolio import forecasts, portfolio
from poptimizer.use_cases import handler
from poptimizer.views import utils

_KEYBOARD_RATIO: Final = 1.5
_LETTER_PREFIX: Final = "letter"
_CASH: Final = "₽"
_OPTIMIZE_BTN: Final = KeyboardButton(text="Portfolio optimization")
_EDIT_BTN: Final = KeyboardButton(text="Position edit")
_MAIN_KEYBOARD: Final = ReplyKeyboardMarkup(
    keyboard=[
        [_OPTIMIZE_BTN, _EDIT_BTN],
    ],
    resize_keyboard=True,
    one_time_keyboard=False,
)


class Dispatcher(aiogram.Dispatcher):
    def __init__(self, chat_id: int, bus: msg.Bus) -> None:
        super().__init__()
        self._lgr = logging.getLogger()
        self._chat_id = chat_id

        self.message(
            aiogram.F.from_user.id != self._chat_id,
        )(self._not_owner)

        self.message(CommandStart())(self._start)

        btn_handlers = (
            (_OPTIMIZE_BTN, self._optimize),
            (_EDIT_BTN, self._edit),
        )

        for btn, btn_handler in btn_handlers:
            self.message(aiogram.F.text == btn.text)(bus.wrap(btn_handler))

    async def _not_owner(self, message: Message) -> None:
        formatting.TextLink("POptimizer", url="https://github.com/WLM1ke/poptimizer")
        msg = formatting.as_list(
            formatting.Bold("You are not bot owner"),
            formatting.as_line(
                "Create your own",
                formatting.TextLink("POptimizer", url="https://github.com/WLM1ke/poptimizer"),
                "bot",
                sep=" ",
            ),
            sep="\n\n",
        )

        await message.answer(msg.as_markdown())

    async def _start(self, message: Message) -> None:
        msg = formatting.as_line(
            "Welcome to",
            formatting.Bold("POptimizer"),
            "bot",
            sep=" ",
        )

        await message.answer(
            msg.as_markdown(),
            reply_markup=_MAIN_KEYBOARD,
        )

    async def _optimize(self, ctx: handler.Ctx, message: Message) -> None:
        forecast = await ctx.get(forecasts.Forecast)

        breakeven, buy, sell = forecast.buy_sell()

        await message.answer(
            formatting.Bold("BUY").as_markdown(),
            reply_markup=_MAIN_KEYBOARD,
        )

        for row in buy:
            msg = formatting.as_list(
                formatting.Bold(f"{row.ticker}"),
                f"Weight: {utils.format_percent(row.weight)}",
                f"Priority: {utils.format_percent(row.grad_lower - breakeven)}",
            )
            await message.answer(
                msg.as_markdown(),
                reply_markup=_MAIN_KEYBOARD,
            )

        if sell:
            await message.answer(
                formatting.Bold("SELL").as_markdown(),
                reply_markup=_MAIN_KEYBOARD,
            )

        for row in sell:
            msg = formatting.as_list(
                formatting.Bold(f"{row.ticker}"),
                f"Weight: {utils.format_percent(row.weight)}",
                f"Priority: {utils.format_percent(row.grad_upper - breakeven)}",
                f"Accounts: {', '.join(row.accounts)}",
            )
            await message.answer(
                msg.as_markdown(),
            )

    async def _edit(self, ctx: handler.Ctx, message: Message) -> None:
        port = await ctx.get(portfolio.Portfolio)

        keys = [InlineKeyboardButton(text=_CASH, callback_data=f"{_LETTER_PREFIX}/{_CASH}")]

        for row in port.positions:
            if (letter := row.ticker[0]) != keys[-1].text:
                keys.append(InlineKeyboardButton(text=letter, callback_data=f"{_LETTER_PREFIX}/{letter}"))

        await message.answer(
            "Choose the first letter of the ticker",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=_keyboard(keys)),
        )


def _keyboard(keys: list[InlineKeyboardButton]) -> list[list[InlineKeyboardButton]]:
    width, rest = divmod((len(keys) * _KEYBOARD_RATIO) ** 0.5, 1)
    if rest:
        width += 1

    return [list(k_row) for k_row in itertools.batched(keys, int(width), strict=False)]
