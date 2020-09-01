"""Базовые структуры данных."""
import enum
from datetime import datetime
from typing import Final, Literal, NamedTuple, Optional

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
INDEX: Final = "MCFTRR"

GroupName = Literal[
    "trading_dates",
    "conomy",
    "dohod",
    "smart_lab",
    "dividends",
    "CPI",
    "securities",
    "MCFTRR",
]


class TableName(NamedTuple):
    """Наименование таблицы."""

    group: GroupName
    name: str


class IndexChecks(enum.Flag):
    """Виды проверок для индекса таблицы."""

    NO_CHECKS = 0  # noqa: WPS115
    UNIQUE = enum.auto()  # noqa: WPS115
    ASCENDING = enum.auto()  # noqa: WPS115
    UNIQUE_ASCENDING = UNIQUE | ASCENDING  # noqa: WPS115


class TableTuple(NamedTuple):
    """Представление таблицы в виде кортежа."""

    group: GroupName
    name: str
    df: pd.DataFrame
    timestamp: datetime
