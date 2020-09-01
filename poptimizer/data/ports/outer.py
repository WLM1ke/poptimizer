"""Интерфейсы служб и вспомогательных типов данных."""
import abc
import datetime
from typing import Dict, Iterable, List, Mapping, NamedTuple, Optional, Tuple

import pandas as pd

from poptimizer.data.domain import model
from poptimizer.data.ports import base


class AbstractEvent(abc.ABC):
    """Абстрактный класс события."""

    def __init__(self) -> None:
        """Создает список для хранения последующих события."""
        self._new_events: List["AbstractEvent"] = []

    @property
    def tables_required(self) -> Tuple[base.TableName, ...]:
        """Перечень таблиц, которые нужны обработчику события."""
        return ()

    @abc.abstractmethod
    def handle_event(self, tables_dict: Dict[base.TableName, model.Table]) -> None:
        """Обрабатывает событие."""

    @property
    def new_events(self) -> List["AbstractEvent"]:
        """События, которые появились во время обработки сообщения."""
        return self._new_events


class TableTuple(NamedTuple):
    """Представление таблицы в виде кортежа."""

    group: base.GroupName
    name: str
    df: pd.DataFrame
    timestamp: datetime.datetime


class AbstractDBSession(abc.ABC):
    """Сессия работы с базой данных."""

    @abc.abstractmethod
    def get(self, table_name: base.TableName) -> Optional[TableTuple]:
        """Получает данные из хранилища."""

    @abc.abstractmethod
    def commit(self, tables_vars: Iterable[TableTuple]) -> None:
        """Сохраняет данные таблиц."""


AbstractTableDescriptionRegistry = Mapping[base.GroupName, base.TableDescription]


class AbstractEventsBus(abc.ABC):
    """Шина для обработки сообщений."""

    @abc.abstractmethod
    def handle_event(self, message: AbstractEvent) -> None:
        """Обработка сообщения и следующих за ним."""


class AbstractViewer(abc.ABC):
    """Позволяет смотреть DataFrame по имени таблицы."""

    @abc.abstractmethod
    def get_df(self, table_name: base.TableName) -> pd.DataFrame:
        """Возвращает DataFrame по имени таблицы."""


class Config(NamedTuple):
    """Описание конфигурации приложения."""

    event_bus: AbstractEventsBus
    viewer: AbstractViewer
    start_date: datetime.date
