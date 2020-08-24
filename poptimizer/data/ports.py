"""Интерфейсы взаимодействия."""
import abc
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

GroupName = Literal["trading_dates", "conomy", "dohod"]


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


AbstractUpdatersRegistry = Mapping[GroupName, AbstractUpdater]
