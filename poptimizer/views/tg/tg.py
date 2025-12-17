import itertools
import logging
from typing import Final

import aiogram
from aiogram.client.bot import Bot
from aiogram.filters.command import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    BotCommand,
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from aiogram.utils import formatting

from poptimizer.controllers.bus import msg
from poptimizer.domain import domain
from poptimizer.domain.portfolio import forecasts, portfolio
from poptimizer.use_cases import handler
from poptimizer.views import utils

_KEYBOARD_RATIO: Final = 1.5
_KEYBOARD_TICKER_MAX_WIDTH: Final = 5

_ACCOUNT_PREFIX: Final = "acc"
_LETTER_PREFIX: Final = "letter"
_TICKER_PREFIX: Final = "ticker"

_CASH: Final = "₽"
_OPTIMIZE_CMD: Final = BotCommand(command="optimize", description="Portfolio optimization")
_EDIT_CMD: Final = BotCommand(command="edit", description="Position edit")

_EDIT_CMD_MSG_ID: Final = "edit_msg_id"


class MenuStates(StatesGroup):
    choosing_account = State()
    choosing_letter = State()
    choosing_ticker = State()
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

        cmd_handlers = (
            (_EDIT_CMD, self._edit_cmd),
            (_OPTIMIZE_CMD, self._optimize_cmd),
        )

        for cmd, cmd_handler in cmd_handlers:
            self.message(Command(cmd.command))(bus.wrap(cmd_handler))

        cb_handlers = (
            (MenuStates.choosing_account, _ACCOUNT_PREFIX, self._account_cb),
            (MenuStates.choosing_letter, _LETTER_PREFIX, self._letter_cb),
        )

        for state, prefix, cb_handler in cb_handlers:
            self.callback_query(state, aiogram.F.data.startswith(prefix))(bus.wrap(cb_handler))

        self.message()(_unknown_msg)

    def bot_commands(self) -> list[BotCommand]:
        return [
            _EDIT_CMD,
            _OPTIMIZE_CMD,
        ]

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

    async def _start_cmd(self, message: Message) -> None:
        msg = formatting.as_line(
            "Welcome to",
            formatting.Bold("POptimizer"),
            "bot",
            sep=" ",
        )

        await message.answer(msg.as_markdown())

    async def _optimize_cmd(self, ctx: handler.Ctx, message: Message, state: FSMContext) -> None:
        forecast = await ctx.get(forecasts.Forecast)

        breakeven, buy, sell = forecast.buy_sell()

        await message.answer(formatting.Bold("BUY").as_markdown())

        for row in buy:
            msg = formatting.as_list(
                formatting.Bold(f"{row.ticker}"),
                f"Weight: {utils.format_percent(row.weight)}",
                f"Priority: {utils.format_percent(row.grad_lower - breakeven)}",
            )
            await message.answer(msg.as_markdown())

        if sell:
            await message.answer(formatting.Bold("SELL").as_markdown())

        for row in sell:
            msg = formatting.as_list(
                formatting.Bold(f"{row.ticker}"),
                f"Weight: {utils.format_percent(row.weight)}",
                f"Priority: {utils.format_percent(row.grad_upper - breakeven)}",
                f"Accounts: {', '.join(row.accounts)}",
            )
            await message.answer(msg.as_markdown())

    async def _edit_cmd(self, ctx: handler.Ctx, message: Message, state: FSMContext, bot: Bot) -> None:
        await self._invalidate_old_edit_cmd(bot, state)

        port = await ctx.get(portfolio.Portfolio)

        msg = await message.answer(
            "Choose account",
            reply_markup=_keyboard(sorted(port.account_names), _ACCOUNT_PREFIX),
        )
        await state.update_data({_EDIT_CMD_MSG_ID: msg.message_id})
        await state.set_state(MenuStates.choosing_account)

    async def _invalidate_old_edit_cmd(self, bot: Bot, state: FSMContext) -> None:
        data = await state.get_data()
        old_msg_id = data.get(_EDIT_CMD_MSG_ID)
        await state.clear()

        if old_msg_id:
            await bot.edit_message_text(
                chat_id=self._chat_id,
                message_id=old_msg_id,
                text="This message is outdated because you sent a new edit command",
                reply_markup=None,
            )

    async def _account_cb(self, ctx: handler.Ctx, callback: CallbackQuery, state: FSMContext) -> None:
        match callback.data, callback.message:
            case str(), Message():
                await state.update_data(account=callback.data.split("/")[1])

                port = await ctx.get(portfolio.Portfolio)
                first_ticker_letters = [_CASH]

                for row in port.positions:
                    if (first_letter := row.ticker[0]) != first_ticker_letters[-1]:
                        first_ticker_letters.append(first_letter)

                await callback.message.edit_text(
                    "Choose first letter of ticker",
                    reply_markup=_keyboard(first_ticker_letters, _LETTER_PREFIX),
                )
                await state.set_state(MenuStates.choosing_letter)
            case _, _:
                ...

        await callback.answer()

    async def _letter_cb(self, ctx: handler.Ctx, callback: CallbackQuery, state: FSMContext) -> None:
        match callback.data, callback.message:
            case str(), Message():
                port = await ctx.get(portfolio.Portfolio)
                first_letter = callback.data.split("/")[1]

                tickers = [row.ticker for row in port.positions if row.ticker.startswith(first_letter)]
                tickers = tickers or [domain.CashTicker]

                match len(tickers):
                    case 1:
                        await state.update_data(ticker=tickers[0])

                        account = await state.get_value("account")

                        await callback.message.edit_text(
                            f"Enter quantity of {tickers[0]} in {account} account",
                            reply_markup=None,
                        )

                        await state.set_state(MenuStates.entering_quantity)
                    case _:
                        await callback.message.edit_text(
                            "Choose ticker",
                            reply_markup=_keyboard(tickers, _TICKER_PREFIX, _KEYBOARD_TICKER_MAX_WIDTH),
                        )
                        await state.set_state(MenuStates.choosing_ticker)
            case _, _:
                ...

        await callback.answer()


async def _unknown_msg(message: Message) -> None:
    await message.answer(formatting.Text("Unknown command - use commands from menu").as_markdown())


def _keyboard[K: str](keys_text: list[K], prefix: str, max_width: int | None = None) -> InlineKeyboardMarkup:
    width, rest = divmod((len(keys_text) * _KEYBOARD_RATIO) ** 0.5, 1)
    if rest:
        width += 1

    if max_width:
        width = min(max_width, width)

    keys = [InlineKeyboardButton(text=key, callback_data=f"{prefix}/{key}") for key in keys_text]
    keyboard = [list(k_row) for k_row in itertools.batched(keys, int(width), strict=False)]

    return InlineKeyboardMarkup(inline_keyboard=keyboard)
