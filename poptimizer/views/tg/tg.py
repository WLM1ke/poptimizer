import contextlib
import itertools
from collections.abc import AsyncIterator
from typing import Final, Self

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
from pydantic import BaseModel

from poptimizer.controllers.bus import msg
from poptimizer.domain import domain
from poptimizer.domain.portfolio import forecasts, portfolio
from poptimizer.use_cases import handler
from poptimizer.views import utils

_KEYBOARD_RATIO: Final = 1.5
_KEYBOARD_TICKER_MAX_WIDTH: Final = 5

_CASH: Final = "₽"
_OPTIMIZE_CMD: Final = BotCommand(command="optimize", description="Portfolio optimization")
_EDIT_CMD: Final = BotCommand(command="edit", description="Position edit")


class EditState(StatesGroup):
    choosing_account = State()
    choosing_letter = State()
    choosing_ticker = State()
    entering_quantity = State()


class EditData(BaseModel):
    msg_id: int = 0
    value: float = 0
    account: domain.AccName = domain.AccName("")
    ticker: domain.Ticker = domain.Ticker("")

    @classmethod
    async def from_state(cls, state: FSMContext) -> Self:
        data = await state.get_data()
        return cls.model_validate(data)

    async def update_state(self, fsm_ctx: FSMContext, state: State) -> None:
        await fsm_ctx.set_data(self.model_dump())
        await fsm_ctx.set_state(state)


def view(chat_id: int, bus: msg.Bus) -> tuple[aiogram.Dispatcher, list[BotCommand]]:
    dp = aiogram.Dispatcher()
    dp.message(
        aiogram.F.from_user.id != chat_id,
    )(_not_owner)

    dp.message(CommandStart())(_start_cmd)
    dp.message(Command(_EDIT_CMD))(bus.wrap(_edit_cmd))
    dp.message(Command(_OPTIMIZE_CMD))(bus.wrap(_optimize_cmd))

    cb_handlers = (
        (EditState.choosing_account, _account_cb),
        (EditState.choosing_letter, _letter_cb),
        (EditState.choosing_ticker, _ticker_cb),
    )

    for state, cb_handler in cb_handlers:
        dp.callback_query(state)(bus.wrap(cb_handler))

    dp.message()(_unknown_msg)

    return dp, [_EDIT_CMD, _OPTIMIZE_CMD]


async def _not_owner(message: Message) -> None:
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


async def _start_cmd(message: Message) -> None:
    msg = formatting.as_line(
        "Welcome to",
        formatting.Bold("POptimizer"),
        "bot",
        sep=" ",
    )

    await message.answer(msg.as_markdown())


async def _optimize_cmd(ctx: handler.Ctx, message: Message) -> None:
    forecast = await ctx.get(forecasts.Forecast)

    breakeven, buy, sell = forecast.buy_sell()

    await message.answer(formatting.Bold("BUY").as_markdown())

    for row in buy:
        msg = formatting.as_list(
            formatting.Bold(f"{row.ticker}"),
            formatting.as_key_value("Weight", utils.format_percent(row.weight)),
            formatting.as_key_value("Priority", utils.format_percent(row.grad_lower - breakeven)),
        )
        await message.answer(msg.as_markdown())

    if sell:
        await message.answer(formatting.Bold("SELL").as_markdown())

    for row in sell:
        msg = formatting.as_list(
            formatting.Bold(f"{row.ticker}"),
            formatting.as_key_value("Weight", utils.format_percent(row.weight)),
            formatting.as_key_value("Priority", utils.format_percent(row.grad_upper - breakeven)),
            formatting.as_key_value("Accounts", ", ".join(row.accounts)),
        )
        await message.answer(msg.as_markdown())


async def _edit_cmd(ctx: handler.Ctx, message: Message, state: FSMContext, bot: Bot) -> None:
    await _invalidate_old_edit_cmd(bot, message.chat.id, state)
    port = await ctx.get(portfolio.Portfolio)

    msg = await message.answer(
        _prompt("Choose account").as_markdown(),
        reply_markup=_keyboard(sorted(port.account_names)),
    )

    await EditData(msg_id=msg.message_id).update_state(state, EditState.choosing_account)


async def _invalidate_old_edit_cmd(bot: Bot, chat_id: int, state: FSMContext) -> None:
    data = await EditData.from_state(state)
    await state.clear()

    if data.msg_id:
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=data.msg_id,
            text=formatting.Strikethrough("Old positions edit").as_markdown(),
            reply_markup=None,
        )


@contextlib.asynccontextmanager
async def _edit_cb_guard(callback: CallbackQuery, state: FSMContext) -> AsyncIterator[tuple[str, Message, EditData]]:
    match callback.data, callback.message:
        case str(), Message():
            yield callback.data, callback.message, await EditData.from_state(state)
        case _, _:
            ...

    await callback.answer()


async def _account_cb(ctx: handler.Ctx, callback: CallbackQuery, state: FSMContext) -> None:
    async with _edit_cb_guard(callback, state) as (cb_data, cb_msg, state_data):
        state_data.account = domain.AccName(cb_data)

        port = await ctx.get(portfolio.Portfolio)
        first_ticker_letters = [_CASH]

        for row in port.positions:
            if (first_letter := row.ticker[0]) != first_ticker_letters[-1]:
                first_ticker_letters.append(first_letter)

        await cb_msg.edit_text(
            formatting.as_list(
                formatting.as_key_value("Account", state_data.account),
                _prompt("Choose first letter of ticker"),
            ).as_markdown(),
            reply_markup=_keyboard(first_ticker_letters),
        )

        await state_data.update_state(state, EditState.choosing_letter)


async def _letter_cb(ctx: handler.Ctx, callback: CallbackQuery, state: FSMContext) -> None:
    async with _edit_cb_guard(callback, state) as (cb_data, cb_msg, state_data):
        port = await ctx.get(portfolio.Portfolio)

        tickers = [row.ticker for row in port.positions if row.ticker.startswith(cb_data)]
        tickers = tickers or [domain.CashTicker]

        match len(tickers):
            case 1:
                state_data.ticker = tickers[0]

                _, pos = port.find_position(state_data.ticker)
                quantity = port.cash_value(state_data.account)
                if pos is not None:
                    quantity = pos.quantity(state_data.account)

                await cb_msg.edit_text(
                    formatting.as_list(
                        formatting.as_key_value("Account", state_data.account),
                        formatting.as_key_value("Ticker", state_data.ticker),
                        formatting.as_key_value("Quantity", quantity),
                        _prompt("Enter new quantity"),
                    ).as_markdown(),
                    reply_markup=None,
                )

                await state_data.update_state(state, EditState.entering_quantity)
            case _:
                await cb_msg.edit_text(
                    formatting.as_list(
                        formatting.as_key_value("Account", state_data.account),
                        _prompt("Choose ticker"),
                    ).as_markdown(),
                    reply_markup=_keyboard(tickers, _KEYBOARD_TICKER_MAX_WIDTH),
                )
                await state.set_state(EditState.choosing_ticker)


async def _ticker_cb(ctx: handler.Ctx, callback: CallbackQuery, state: FSMContext) -> None:
    async with _edit_cb_guard(callback, state) as (cb_data, cb_msg, state_data):
        port = await ctx.get(portfolio.Portfolio)
        state_data.ticker = domain.Ticker(cb_data)

        _, pos = port.find_position(state_data.ticker)
        quantity = port.cash_value(state_data.account)
        if pos is not None:
            quantity = pos.quantity(state_data.account)

        await cb_msg.edit_text(
            formatting.as_list(
                formatting.as_key_value("Account", state_data.account),
                formatting.as_key_value("Ticker", state_data.ticker),
                formatting.as_key_value("Quantity", quantity),
                _prompt("Enter new quantity"),
            ).as_markdown(),
            reply_markup=None,
        )

        await state_data.update_state(state, EditState.entering_quantity)


async def _unknown_msg(message: Message) -> None:
    await message.answer(formatting.as_key_value("Unknown command", "use menu").as_markdown())


def _keyboard[K: str](keys_text: list[K], max_width: int | None = None) -> InlineKeyboardMarkup:
    width, rest = divmod((len(keys_text) * _KEYBOARD_RATIO) ** 0.5, 1)
    if rest:
        width += 1

    if max_width:
        width = min(max_width, width)

    keys = [InlineKeyboardButton(text=key, callback_data=f"{key}") for key in keys_text]
    keyboard = [list(k_row) for k_row in itertools.batched(keys, int(width), strict=False)]

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def _prompt(prompt: str) -> formatting.Text:
    return formatting.Text(f"\n{prompt}...")
