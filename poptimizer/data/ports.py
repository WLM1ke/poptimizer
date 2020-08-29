"""Интерфейсы взаимодействия."""
import abc
import enum
from datetime import datetime
from typing import Final, Iterable, Literal, Mapping, NamedTuple, Optional

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

GroupName = Literal["trading_dates", "conomy", "dohod", "smart_lab", "dividends", "CPI"]


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


class AbstractDBSession(abc.ABC):
    """Сессия работы с базой данных."""

    @abc.abstractmethod
    def get(self, table_name: TableName) -> Optional[TableTuple]:
        """Получает данные из хранилища."""

    @abc.abstractmethod
    def commit(self, tables_vars: Iterable[TableTuple]) -> None:
        """Сохраняет данные таблиц."""


class AbstractUpdater(abc.ABC):
    """Обновляет конкретную группу таблиц."""

    @abc.abstractmethod
    def __call__(self, table_name: TableName) -> pd.DataFrame:
        """Загружает обновление."""


class IndexChecks(enum.Flag):
    """Виды проверок для индекса таблицы."""

    NO_CHECKS = 0  # noqa: WPS115
    UNIQUE = enum.auto()  # noqa: WPS115
    ASCENDING = enum.auto()  # noqa: WPS115
    UNIQUE_ASCENDING = UNIQUE | ASCENDING  # noqa: WPS115


class ValType(enum.Enum):
    """Виды проверок для индекса таблицы."""

    NO_VAL = enum.auto()  # noqa: WPS115
    LAST = enum.auto()  # noqa: WPS115
    ALL = enum.auto()  # noqa: WPS115


class TableDescription(NamedTuple):
    """Описание типа таблицы."""

    updater: AbstractUpdater
    index_checks: IndexChecks
    validation_type: ValType


AbstractTableDescriptionRegistry = Mapping[GroupName, TableDescription]
