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


class ValType(enum.Enum):
    """Виды проверок для индекса таблицы."""

    NO_VAL = enum.auto()  # noqa: WPS115
    LAST = enum.auto()  # noqa: WPS115
    ALL = enum.auto()  # noqa: WPS115


class TableDescription(NamedTuple):
    """Описание типа таблицы."""

    updater: outer.AbstractUpdater
    index_checks: IndexChecks
    validation_type: ValType


AbstractTableDescriptionRegistry = Mapping[base.GroupName, TableDescription]
