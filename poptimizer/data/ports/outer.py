"""Интерфейсы внешней инфраструктуры."""
import abc
import datetime
from typing import Iterable, Optional, Union

import pandas as pd

from poptimizer.data.ports import base


class AbstractDBSession(abc.ABC):
    """Сессия работы с базой данных."""

    @abc.abstractmethod
    def get(self, table_name: base.TableName) -> Optional[base.TableTuple]:
        """Получает данные из хранилища."""

    @abc.abstractmethod
    def commit(self, tables_vars: Iterable[base.TableTuple]) -> None:
        """Сохраняет данные таблиц."""


class AbstractLoader(abc.ABC):
    """Обновляет конкретную группу таблиц."""

    @abc.abstractmethod
    def __call__(self, table_name: base.TableName) -> pd.DataFrame:
        """Загружает данные обновления полностью."""


class AbstractIncrementalLoader(abc.ABC):
    """Обновляет конкретную группу таблиц."""

    @abc.abstractmethod
    def __call__(self, table_name: base.TableName, start_date: datetime.date) -> pd.DataFrame:
        """Загружает данные обновления начиная с некой даты."""


Loaders = Union[AbstractLoader, AbstractIncrementalLoader]
