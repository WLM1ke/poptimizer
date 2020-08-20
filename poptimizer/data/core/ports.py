"""Интерфейсы взаимодействия."""
import abc
from datetime import datetime
from typing import Iterable, NamedTuple, Optional, Tuple

import pandas as pd


class AbstractUpdater(abc.ABC):
    """Обновляет конкретную группу таблиц."""

    @abc.abstractmethod
    def need_update(self, timestamp: datetime) -> bool:
        """Проверяет необходимость обновления."""

    @abc.abstractmethod
    def get_update(self) -> pd.DataFrame:
        """Загружает обновление."""


class TableTuple(NamedTuple):
    """Представление таблицы в виде кортежа."""

    group: str
    id_: str
    df: pd.DataFrame
    timestamp: datetime


class AbstractDBSession(abc.ABC):
    """Сессия работы с базой данных."""

    @abc.abstractmethod
    def get(self, name: Tuple[str, str]) -> Optional[TableTuple]:
        """Получает данные из хранилища."""

    @abc.abstractmethod
    def commit(self, tables_vars: Iterable[TableTuple]) -> None:
        """Сохраняет данные таблиц."""
