"""Базовые типы, необходимые для описания таблицы с данными."""
import abc
import enum
from typing import Final, Literal, NamedTuple, Optional, Union

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
QUOTES: Final = "quotes"

GroupName = Literal[
    "trading_dates",
    "conomy",
    "dohod",
    "smart_lab",
    "dividends",
    "CPI",
    "securities",
    "MCFTRR",
    "quotes",
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


class AbstractLoader(abc.ABC):
    """Загружает обновление для таблицы полностью."""

    @abc.abstractmethod
    async def get(self, table_name: TableName) -> pd.DataFrame:
        """Загружает данные."""


class AbstractIncrementalLoader(abc.ABC):
    """Загружает обновление для таблицы с некоторой даты."""

    @abc.abstractmethod
    async def get(
        self,
        table_name: TableName,
        last_index: Optional[str] = None,
    ) -> pd.DataFrame:
        """Загружает данные обновления начиная с некой даты.

        При отсутствии даты загружает все данные.
        """


Loaders = Union[AbstractLoader, AbstractIncrementalLoader]


class TableDescription(NamedTuple):
    """Описание правил обновления таблицы."""

    loader: Loaders
    index_checks: IndexChecks
    validate: bool
