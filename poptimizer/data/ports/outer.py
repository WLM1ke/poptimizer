"""Интерфейсы внешних служб и вспомогательных типов данных."""
import abc
import datetime
from typing import Final, Iterable, Literal, NamedTuple, Optional, Union

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
INDEX: Final = "indexes"
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


class TableTuple(NamedTuple):
    """Представление таблицы в виде кортежа."""

    group: GroupName
    name: str
    df: pd.DataFrame
    timestamp: datetime.datetime


class AbstractDBSession(abc.ABC):
    """Сессия работы с базой данных."""

    @abc.abstractmethod
    async def get(self, table_name: TableName) -> Optional[TableTuple]:
        """Получает данные из хранилища."""

    @abc.abstractmethod
    async def commit(self, tables_vars: Iterable[TableTuple]) -> None:
        """Сохраняет данные таблиц."""
