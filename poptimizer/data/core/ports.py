"""Интерфейсы взаимодействия."""
import abc
from datetime import datetime
from typing import Iterable, Optional, Tuple, TypedDict

import pandas as pd


class AbstractUpdater(abc.ABC):
    """Обновляет конкретную группу таблиц."""

    @abc.abstractmethod
    def need_update(self, timestamp: datetime) -> bool:
        """Проверяет необходимость обновления."""

    @abc.abstractmethod
    def get_update(self) -> pd.DataFrame:
        """Загружает обновление."""


class TableVars(TypedDict):
    """Представление таблицы в виде словаря."""

    group: str
    _id: str
    df: pd.DataFrame
    timestamp: datetime


class AbstractDBSession(abc.ABC):
    """Сессия работы с базой данных."""

    @abc.abstractmethod
    def get(self, name: Tuple[str, str]) -> Optional[TableVars]:
        """Получает данные из хранилища."""

    @abc.abstractmethod
    def commit(self, tables_vars: Iterable[TableVars]) -> None:
        """Сохраняет данные таблиц."""
