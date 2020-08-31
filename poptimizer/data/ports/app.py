"""Интерфейс регистра с описанием таблиц."""
import enum
from typing import Mapping, NamedTuple

from poptimizer.data.ports import base, outer


class IndexChecks(enum.Flag):
    """Виды проверок для индекса таблицы."""

    NO_CHECKS = 0  # noqa: WPS115
    UNIQUE = enum.auto()  # noqa: WPS115
    ASCENDING = enum.auto()  # noqa: WPS115
    UNIQUE_ASCENDING = UNIQUE | ASCENDING  # noqa: WPS115


class TableDescription(NamedTuple):
    """Описание типа таблицы."""

    updater: outer.Updaters
    index_checks: IndexChecks
    validate: bool


AbstractTableDescriptionRegistry = Mapping[base.GroupName, TableDescription]


class Config(NamedTuple):
    """Описание конфигурации приложения."""

    db_session: outer.AbstractDBSession
    description_registry: AbstractTableDescriptionRegistry
