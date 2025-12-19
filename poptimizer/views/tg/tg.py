import contextlib
from collections.abc import AsyncIterator
from typing import Final

import aiogram
from aiogram.client.bot import Bot
from aiogram.filters.command import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    BotCommand,
    CallbackQuery,
    Message,
)

from poptimizer.controllers.bus import msg
from poptimizer.domain import domain
from poptimizer.domain.portfolio import forecasts, portfolio
from poptimizer.use_cases import handler
from poptimizer.views.tg import model, view

_KEYBOARD_TICKER_MAX_WIDTH: Final = 5

_CASH: Final = "₽"
_OPTIMIZE_CMD: Final = BotCommand(command="optimize", description="Portfolio optimization")
_EDIT_CMD: Final = BotCommand(command="edit", description="Position edit")


class EditState(StatesGroup):
    choosing_account = State()
    choosing_letter = State()
    choosing_ticker = State()
    entering_quantity = State()


def dispatcher(chat_id: int, bus: msg.Bus) -> tuple[aiogram.Dispatcher, list[BotCommand]]:
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
    await message.answer(view.not_owner())


async def _start_cmd(message: Message) -> None:
    await message.answer(view.start_welcome())


async def _optimize_cmd(ctx: handler.Ctx, message: Message) -> None:
    forecast = await ctx.get(forecasts.Forecast)

    breakeven, buy, sell = forecast.buy_sell()

    await message.answer(view.optimize_buy_section())

    for row in buy:
        await message.answer(view.optimize_buy_ticker(row, breakeven))

    if sell:
        await message.answer(view.optimize_sell_section())

    for row in sell:
        await message.answer(view.optimize_sell_ticker(row, breakeven))


async def _edit_cmd(ctx: handler.Ctx, message: Message, state: FSMContext, bot: Bot) -> None:
    await _clear_old_edit(bot, message.chat.id, state)
    port = await ctx.get(portfolio.Portfolio)

    msg = await message.answer(
        view.edit_choose_account(),
        reply_markup=view.keyboard(sorted(port.account_names)),
    )

    await model.Edit(msg_id=msg.message_id).update_state(state, EditState.choosing_account)


async def _clear_old_edit(bot: Bot, chat_id: int, state: FSMContext) -> None:
    data = await model.edit(state)
    await state.clear()

    if data.msg_id:
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=data.msg_id,
            text=view.edit_terminated(),
            reply_markup=None,
        )


@contextlib.asynccontextmanager
async def _edit_cb_guard(callback: CallbackQuery, state: FSMContext) -> AsyncIterator[tuple[str, Message, model.Edit]]:
    match callback.data, callback.message:
        case str(), Message():
            yield callback.data, callback.message, await model.edit(state)
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
            view.edit_choose_first_letter(state_data),
            reply_markup=view.keyboard(first_ticker_letters),
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

                await cb_msg.edit_text(view.edit_enter_quantity(state_data, quantity))
                await state_data.update_state(state, EditState.entering_quantity)
            case _:
                await cb_msg.edit_text(
                    view.edit_choose_ticker(state_data),
                    reply_markup=view.keyboard(tickers, _KEYBOARD_TICKER_MAX_WIDTH),
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

        await cb_msg.edit_text(view.edit_enter_quantity(state_data, quantity))
        await state_data.update_state(state, EditState.entering_quantity)


async def _unknown_msg(message: Message) -> None:
    await message.answer(view.unknown_command())
