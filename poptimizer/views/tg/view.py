import itertools
from typing import Final

from aiogram.types.inline_keyboard_button import InlineKeyboardButton
from aiogram.types.inline_keyboard_markup import InlineKeyboardMarkup
from aiogram.utils import formatting

from poptimizer.domain.portfolio import forecasts
from poptimizer.views import utils
from poptimizer.views.tg import model

_KEYBOARD_RATIO: Final = 1.5


def keyboard[K: str](keys_text: list[K], max_width: int | None = None) -> InlineKeyboardMarkup:
    width, rest = divmod((len(keys_text) * _KEYBOARD_RATIO) ** 0.5, 1)
    if rest:
        width += 1

    if max_width:
        width = min(max_width, width)

    keys = [InlineKeyboardButton(text=key, callback_data=f"{key}") for key in keys_text]
    keyboard = [list(k_row) for k_row in itertools.batched(keys, int(width), strict=False)]

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def start_welcome() -> str:
    return formatting.as_line(
        "Welcome to",
        formatting.Bold("POptimizer"),
        "bot",
        sep=" ",
    ).as_markdown()


def not_owner() -> str:
    return formatting.as_list(
        formatting.Bold("You are not bot owner\n"),
        formatting.as_line(
            "Create your own",
            formatting.TextLink("POptimizer", url="https://github.com/WLM1ke/poptimizer"),
            "bot",
            sep=" ",
        ),
    ).as_markdown()


def unknown_command() -> str:
    return formatting.as_key_value("Unknown command", "use menu").as_markdown()


def optimize_buy_section() -> str:
    return formatting.Bold("BUY").as_markdown()


def optimize_buy_ticker(pos: forecasts.Position, breakeven: float) -> str:
    return formatting.as_list(
        formatting.Bold(f"{pos.ticker}"),
        formatting.as_key_value("Weight", utils.format_percent(pos.weight)),
        formatting.as_key_value("Priority", utils.format_percent(pos.grad_lower - breakeven)),
    ).as_markdown()


def optimize_sell_section() -> str:
    return formatting.Bold("SELL").as_markdown()


def optimize_sell_ticker(pos: forecasts.Position, breakeven: float) -> str:
    return formatting.as_list(
        formatting.Bold(f"{pos.ticker}"),
        formatting.as_key_value("Weight", utils.format_percent(pos.weight)),
        formatting.as_key_value("Priority", utils.format_percent(pos.grad_upper - breakeven)),
        formatting.as_key_value("Accounts", ", ".join(pos.accounts)),
    ).as_markdown()


def _prompt(prompt: str) -> formatting.Text:
    return formatting.Text(f"\n{prompt}...")


def edit_choose_account() -> str:
    return _prompt("Choose account").as_markdown()


def edit_choose_first_letter(edit: model.Edit) -> str:
    return formatting.as_list(
        formatting.as_key_value("Account", edit.account),
        _prompt("Choose first letter of ticker"),
    ).as_markdown()


def edit_choose_ticker(edit: model.Edit) -> str:
    return formatting.as_list(
        formatting.as_key_value("Account", edit.account),
        _prompt("Choose ticker"),
    ).as_markdown()


def edit_enter_quantity(edit: model.Edit) -> str:
    return formatting.as_list(
        formatting.as_key_value("Account", edit.account),
        formatting.as_key_value("Ticker", edit.ticker),
        formatting.as_key_value("Quantity", utils.format_float(edit.quantity, 0)),
        _prompt("Enter new quantity"),
    ).as_markdown()


def edit_invalid_quantity(err: str) -> str:
    return formatting.as_list(
        formatting.as_key_value("Error", formatting.Text(err)),
        _prompt("Enter new quantity"),
    ).as_markdown()


def new_quantity(edit: model.Edit) -> str:
    return formatting.as_list(
        formatting.as_key_value("Account", edit.account),
        formatting.as_key_value("Ticker", edit.ticker),
        formatting.as_key_value("Quantity", edit.quantity),
        formatting.as_key_value("Value", utils.format_float(edit.value, 0)),
        _prompt("Choose first letter of next ticker"),
    ).as_markdown()


def edit_escape(edit: model.Edit, value: float) -> str:
    return formatting.as_list(
        formatting.as_key_value("Account", edit.account),
        formatting.as_key_value("Edited tickers", ", ".join(edit.unique_edited_tickers)),
        formatting.Bold("\nValue changed:"),
        formatting.Text(f"{utils.format_float(edit.acc_value, 0)} ₽"),
        formatting.Text(f"{utils.format_float(value, 0)} ₽"),
    ).as_markdown()
