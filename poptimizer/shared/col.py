"""Наименование столбцов и константы."""
from typing import Final

# Наименования столбцов
DATE: Final = "DATE"
TICKER: Final = "TICKER"
DIVIDENDS: Final = "DIVIDENDS"
CPI: Final = "CPI"
ISIN: Final = "ISIN"
MARKET: Final = "MARKET"
SHARE_TYPE: Final = "SHARE_TYPE"
LOT_SIZE: Final = "LOT_SIZE"
OPEN: Final = "OPEN"
CLOSE: Final = "CLOSE"
HIGH: Final = "HIGH"
LOW: Final = "LOW"
TURNOVER: Final = "TURNOVER"

# Типы ценных бумаг
ORDINARY: Final = 0
PREFERRED: Final = 1
FOREIGN: Final = 2
ETF: Final = 3
