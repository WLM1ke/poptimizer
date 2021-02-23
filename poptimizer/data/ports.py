"""Наименование существующих таблиц."""
from typing import Final, Literal

TRADING_DATES: Final = "trading_dates"
DIV_NEW: Final = "div_new"
DIVIDENDS: Final = "dividends"
DIV_EXT: Final = "div_ext"
CPI: Final = "CPI"
SECURITIES: Final = "securities"
INDEX: Final = "indexes"
QUOTES: Final = "quotes"
USD: Final = "usd"

GroupName = Literal[
    "trading_dates",
    "div_new",
    "dividends",
    "div_ext",
    "CPI",
    "securities",
    "indexes",
    "quotes",
    "usd",
]
