"""Базовые структуры данных."""
from datetime import datetime
from typing import Final, Literal, NamedTuple

import pandas as pd

from poptimizer.config import POptimizerError


class DataError(POptimizerError):
    """Ошибки связанные с операциями по обновлению данных."""


# Наименования групп таблиц
TRADING_DATES: Final = "trading_dates"
CONOMY: Final = "conomy"
DOHOD: Final = "dohod"
SMART_LAB: Final = "smart_lab"
DIVIDENDS: Final = "dividends"
CPI: Final = "CPI"
SECURITIES: Final = "securities"

GroupName = Literal["trading_dates", "conomy", "dohod", "smart_lab", "dividends", "CPI", "securities"]


class TableName(NamedTuple):
    """Наименование таблицы."""

    group: GroupName
    name: str


class TableTuple(NamedTuple):
    """Представление таблицы в виде кортежа."""

    group: GroupName
    name: str
    df: pd.DataFrame
    timestamp: datetime
