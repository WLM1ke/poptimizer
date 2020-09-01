"""Интерфейс регистра с описанием таблиц."""
import abc
import datetime
from typing import Mapping, NamedTuple

import pandas as pd

from poptimizer.data.ports import base, domain
from poptimizer.data.ports.outer import TableDescription

AbstractTableDescriptionRegistry = Mapping[base.GroupName, TableDescription]


class AbstractEventsBus(abc.ABC):
    """Шина для обработки сообщений."""

    @abc.abstractmethod
    def handle_event(self, message: domain.AbstractEvent) -> None:
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
