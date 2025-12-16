import itertools
import logging
from typing import Final

import aiogram
from aiogram.filters.command import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
)
from aiogram.utils import formatting

from poptimizer.controllers.bus import msg
from poptimizer.domain import domain
from poptimizer.domain.portfolio import forecasts, portfolio
from poptimizer.use_cases import handler
from poptimizer.views import utils

_KEYBOARD_RATIO: Final = 1.5
_KEYBOARD_MAX_WIDTH: Final = 5
_LETTER_PREFIX: Final = "letter"
_TICKER_PREFIX: Final = "ticker"
_ACCOUNT_PREFIX: Final = "acc"
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


class MenuStates(StatesGroup):
    choosing_letter = State()
    choosing_ticker = State()
    choosing_account = State()
    entering_quantity = State()


class Dispatcher(aiogram.Dispatcher):
    def __init__(self, chat_id: int, bus: msg.Bus) -> None:
        super().__init__()
        self._lgr = logging.getLogger()
        self._chat_id = chat_id

        self.message(
            aiogram.F.from_user.id != self._chat_id,
        )(self._not_owner)

        self.message(CommandStart())(self._start_cmd)

        btn_handlers = (
            (_OPTIMIZE_BTN, self._optimize_btn),
            (_EDIT_BTN, self._edit_btn),
        )

        for btn, btn_handler in btn_handlers:
            self.message(aiogram.F.text == btn.text)(bus.wrap(btn_handler))

        self.callback_query(MenuStates.choosing_letter, aiogram.F.data.startswith(_LETTER_PREFIX))(
            bus.wrap(self._letter_cb)
        )

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

    async def _start_cmd(self, message: Message, state: FSMContext) -> None:
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
        await state.clear()

    async def _optimize_btn(self, ctx: handler.Ctx, message: Message, state: FSMContext) -> None:
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
        await state.clear()

    async def _edit_btn(self, ctx: handler.Ctx, message: Message, state: FSMContext) -> None:
        port = await ctx.get(portfolio.Portfolio)

        first_ticker_letters = [_CASH]

        for row in port.positions:
            if (first_letter := row.ticker[0]) != first_ticker_letters[-1]:
                first_ticker_letters.append(first_letter)

        await message.answer(
            "Choose first letter of ticker to edit",
            reply_markup=_keyboard(first_ticker_letters, _LETTER_PREFIX),
        )
        await state.set_state(MenuStates.choosing_letter)

    async def _letter_cb(self, ctx: handler.Ctx, callback: CallbackQuery, state: FSMContext) -> None:
        match callback.data, callback.message:
            case str(), Message():
                port = await ctx.get(portfolio.Portfolio)
                first_letter = callback.data.split("/")[1]

                tickers = [row.ticker for row in port.positions if row.ticker.startswith(first_letter)]
                tickers = tickers or [domain.CashTicker]

                match len(tickers):
                    case 1:
                        port = await ctx.get(portfolio.Portfolio)
                        await callback.message.edit_text(
                            f"Choose account for {tickers[0]} to edit",
                            reply_markup=_keyboard(sorted(port.account_names), _ACCOUNT_PREFIX),
                        )
                        await state.set_state(MenuStates.choosing_account)
                    case _:
                        await callback.message.edit_text(
                            "Choose ticker to edit",
                            reply_markup=_keyboard(tickers, _TICKER_PREFIX),
                        )
                        await state.set_state(MenuStates.choosing_letter)

                await callback.answer()
            case _, _:
                ...


def _keyboard[K: str](keys_text: list[K], prefix: str) -> InlineKeyboardMarkup:
    width, rest = divmod((len(keys_text) * _KEYBOARD_RATIO) ** 0.5, 1)
    if rest:
        width += 1

    width = min(_KEYBOARD_MAX_WIDTH, int(width))

    keys = [InlineKeyboardButton(text=key, callback_data=f"{prefix}/{key}") for key in keys_text]
    keyboard = [list(k_row) for k_row in itertools.batched(keys, width, strict=False)]

    return InlineKeyboardMarkup(inline_keyboard=keyboard)
