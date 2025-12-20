import contextlib
import re
from collections.abc import AsyncIterator
from typing import Final

import aiogram
from aiogram.client.bot import Bot
from aiogram.filters.command import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.pymongo import PyMongoStorage
from aiogram.types import (
    BotCommand,
    CallbackQuery,
    Message,
)

from poptimizer import errors
from poptimizer.adapters import mongo
from poptimizer.controllers.bus import msg
from poptimizer.domain import domain
from poptimizer.domain.portfolio import forecasts, portfolio
from poptimizer.use_cases import handler
from poptimizer.views.tg import model, view

_FSM_MONGO_COLLECTION: Final = "TgFSM"


_OPTIMIZE_CMD: Final = BotCommand(command="optimize", description="Portfolio optimization")
_EDIT_CMD: Final = BotCommand(command="edit", description="Edit account")

_KEYBOARD_TICKER_MAX_WIDTH: Final = 5
_CASH_BTN: Final = "₽"
_ESCAPE_BTN: Final = "␛"

_RE_SPACES: Final = re.compile(r"\s+")


class EditState(StatesGroup):
    choosing_account = State()
    choosing_letter = State()
    choosing_ticker = State()
    entering_quantity = State()


def dispatcher(
    chat_id: int,
    mong_db: mongo.MongoDatabase,
    bus: msg.Bus,
) -> tuple[aiogram.Dispatcher, list[BotCommand]]:
    storage = PyMongoStorage(mong_db.client, db_name=mong_db.name, collection_name=_FSM_MONGO_COLLECTION)
    dp = aiogram.Dispatcher(storage=storage)
    dp.message(
        aiogram.F.from_user.id != chat_id,
    )(_not_owner)

    dp.message(CommandStart())(_start_cmd)
    dp.message(Command(_EDIT_CMD))(bus.wrap(_edit_cmd))
    dp.message(Command(_OPTIMIZE_CMD))(bus.wrap(_optimize_cmd))

    dp.callback_query(EditState.choosing_account)(bus.wrap(_account_cb))
    dp.callback_query(EditState.choosing_letter)(bus.wrap(_letter_cb))
    dp.callback_query(EditState.choosing_ticker)(bus.wrap(_ticker_cb))

    dp.message(EditState.entering_quantity)(bus.wrap(_quantity_msg))

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

    if not sell:
        return

    await message.answer(view.optimize_sell_section())

    for row in sell:
        await message.answer(view.optimize_sell_ticker(row, breakeven))


async def _edit_cmd(ctx: handler.Ctx, message: Message, state: FSMContext, bot: Bot) -> None:
    await _clear_old_keyboard(bot, message.chat.id, state)
    port = await ctx.get(portfolio.Portfolio)

    send_msg = await message.answer(
        view.edit_choose_account(),
        reply_markup=view.keyboard(sorted(port.account_names)),
    )

    await model.Edit(msg_id=send_msg.message_id).update_state(state, EditState.choosing_account)


async def _clear_old_keyboard(bot: Bot, chat_id: int, state: FSMContext) -> None:
    state_data = await model.edit(state)
    await state.clear()

    if state_data.msg_id:
        await bot.edit_message_reply_markup(
            chat_id=chat_id,
            message_id=state_data.msg_id,
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


def _first_ticker_letters(port: portfolio.Portfolio, *, with_escape: bool = False) -> list[str]:
    first_ticker_letters = [_CASH_BTN]

    for row in port.positions:
        if (first_letter := row.ticker[0]) != first_ticker_letters[-1]:
            first_ticker_letters.append(first_letter)

    if with_escape:
        first_ticker_letters.append(_ESCAPE_BTN)

    return first_ticker_letters


async def _account_cb(ctx: handler.Ctx, callback: CallbackQuery, state: FSMContext) -> None:
    async with _edit_cb_guard(callback, state) as (cb_data, cb_msg, state_data):
        port = await ctx.get(portfolio.Portfolio)

        state_data.account = domain.AccName(cb_data)
        state_data.acc_value = port.value(state_data.account)

        await cb_msg.edit_text(
            view.edit_choose_first_letter(state_data),
            reply_markup=view.keyboard(_first_ticker_letters(port)),
        )

        await state_data.update_state(state, EditState.choosing_letter)


async def _escape(state: FSMContext, cb_msg: Message, state_data: model.Edit, acc_value: float) -> None:
    await cb_msg.edit_text(view.edit_escape(state_data, acc_value))
    await state.clear()


async def _letter_cb(ctx: handler.Ctx, callback: CallbackQuery, state: FSMContext) -> None:
    async with _edit_cb_guard(callback, state) as (cb_data, cb_msg, state_data):
        port = await ctx.get(portfolio.Portfolio)

        tickers = [row.ticker for row in port.positions if row.ticker.startswith(cb_data)]

        match tickers:
            case [] if cb_data == _CASH_BTN:
                state_data.ticker = domain.CashTicker
                state_data.quantity = port.cash_value(state_data.account)
                state_data.msg_id = 0

                await cb_msg.edit_text(view.edit_enter_quantity(state_data))
                await state_data.update_state(state, EditState.entering_quantity)
            case []:
                await _escape(state, cb_msg, state_data, port.value(state_data.account))
            case [ticker]:
                _, pos = port.find_position(ticker)
                if pos is None:
                    await _escape(state, cb_msg, state_data, port.value(state_data.account))

                    return

                state_data.ticker = ticker
                state_data.quantity = pos.quantity(state_data.account)
                state_data.msg_id = 0

                await cb_msg.edit_text(view.edit_enter_quantity(state_data))
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
        ticker = domain.Ticker(cb_data)

        _, pos = port.find_position(ticker)
        if pos is None:
            await _escape(state, cb_msg, state_data, port.value(state_data.account))

            return

        state_data.ticker = ticker
        state_data.quantity = pos.quantity(state_data.account)
        state_data.msg_id = 0

        await cb_msg.edit_text(view.edit_enter_quantity(state_data))
        await state_data.update_state(state, EditState.entering_quantity)


def _parse_quantity(message: Message) -> int:
    quantity = message.text or ""

    try:
        return int(_RE_SPACES.sub("", quantity or ""))
    except ValueError as err:
        raise errors.ControllersError(f"quantity {quantity} should be number") from err


async def _quantity_msg(ctx: handler.Ctx, message: Message, state: FSMContext) -> None:
    state_data = await model.edit(state)
    port = await ctx.get_for_update(portfolio.Portfolio)

    try:
        state_data.quantity = _parse_quantity(message)
        port.update_position(state_data.account, state_data.ticker, state_data.quantity)
    except (errors.ControllersError, errors.DomainError) as err:
        await message.answer(view.edit_invalid_quantity(str(err)))

        return

    _, pos = port.find_position(state_data.ticker)
    match pos:
        case None:
            state_data.value = port.cash_value(state_data.account)
        case _:
            state_data.value = pos.value(state_data.account)

    send_msg = await message.answer(
        view.new_quantity(state_data),
        reply_markup=view.keyboard(_first_ticker_letters(port, with_escape=True)),
    )
    state_data.msg_id = send_msg.message_id
    state_data.edited_tickers.append(state_data.ticker)

    await state_data.update_state(state, EditState.choosing_letter)


async def _unknown_msg(message: Message) -> None:
    await message.answer(view.unknown_command())
