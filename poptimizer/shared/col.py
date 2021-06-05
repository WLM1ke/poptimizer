"""Наименование столбцов и константы."""
from typing import Final, Literal

# Наименования столбцов
DATE: Final = "DATE"
TICKER: Final = "TICKER"
DIVIDENDS: Final = "DIVIDENDS"
CPI: Final = "CPI"
ISIN: Final = "ISIN"
MARKET: Final = "MARKET"
TICKER_TYPE: Final = "TICKER_TYPE"
LOT_SIZE: Final = "LOT_SIZE"
TURNOVER: Final = "TURNOVER"
CURRENCY: Final = "CURRENCY"

RF: Final = "RF"

OPEN: Final = "OPEN"
CLOSE: Final = "CLOSE"
HIGH: Final = "HIGH"
LOW: Final = "LOW"
PriceType = Literal["OPEN", "CLOSE", "HIGH", "LOW"]

# Типы валют
RUR: Final = "RUR"
USD: Final = "USD"

# Типы ценных бумаг
TYPES_N: Final = 4
ORDINARY, PREFERRED, FOREIGN, ETF = range(TYPES_N)
