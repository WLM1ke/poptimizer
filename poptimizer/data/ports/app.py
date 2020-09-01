"""Интерфейс регистра с описанием таблиц."""
import datetime
from typing import Mapping, NamedTuple

from poptimizer.data.ports import base, outer
from poptimizer.data.ports.base import IndexChecks


class TableDescription(NamedTuple):
    """Описание правил обновления таблицы."""

    loader: outer.Loaders
    index_checks: IndexChecks
    validate: bool


AbstractTableDescriptionRegistry = Mapping[base.GroupName, TableDescription]


class Config(NamedTuple):
    """Описание конфигурации приложения."""

    db_session: outer.AbstractDBSession
    description_registry: AbstractTableDescriptionRegistry
    start_date: datetime.date
