"""Основные классы модели данных - таблица и реестр таблиц."""
from datetime import datetime
from typing import Dict, NamedTuple, Optional

import pandas as pd

from poptimizer.config import POptimizerError
from poptimizer.data.core import ports


class TableError(POptimizerError):
    """Ошибки связанные с созданием и обновлением таблиц."""


class TableSpec(NamedTuple):
    """Описание разновидности таблицы с данными, особенностей обновления и валидации.

    - множество таблиц данного типа
    - возможность инкрементального обновления или только полной загрузки
    - уникальный индекс
    - возрастающий индекс
    """

    updater: ports.AbstractUpdater


class TablesRegistry:
    """Реестр спецификации таблиц."""

    def __init__(self) -> None:
        """Создает пустой реестр."""
        self._registry: Dict[str, TableSpec] = {}

    def create_registry(self, spec: Dict[str, TableSpec]) -> None:
        """Создает реестр на основе спецификации таблиц в реестр."""
        self._registry = dict(spec)

    def get_specs(self, name: ports.TableName) -> TableSpec:
        """Получает спецификацию для таблицы."""
        table_group = name.group
        return self._registry[table_group]


registry = TablesRegistry()


class Table:
    """Базовый класс таблицы с данными."""

    def __init__(
        self, name: ports.TableName, df: pd.DataFrame, timestamp: Optional[datetime] = None,
    ):
        """При создании и последующем обновлении автоматически сохраняется момент UTC.

        Осуществляется проверка, что имя есть в реестре таблиц.

        :param name:
            Наименование, если тип имеет множество таблиц.
        :param df:
            Таблица.
        :param timestamp:
            Момент последнего обновления.
        :raises TableError:
            Имя отсутствует в реестре.
        """
        try:
            registry.get_specs(name)
        except KeyError:
            raise TableError(f"Имя отсутствует в реестре - {name}")
        self._name = name
        self._df = df
        self._timestamp: datetime = timestamp or datetime.utcnow()

    def __str__(self) -> str:
        """Отображает название класса и таблицы."""
        return f"{self.__class__.__name__}({', '.join(self._name)})"

    @property
    def df(self) -> pd.DataFrame:
        """Таблица с данными."""
        return self._df.copy()

    @df.setter
    def df(self, df: pd.DataFrame) -> None:
        """Устанавливает новое значение и обновляет момент обновления UTC."""
        self._timestamp = datetime.utcnow()
        self._df = df

    @property
    def timestamp(self) -> datetime:
        """Момент обновления данных UTC."""
        return self._timestamp

    @property
    def name(self) -> ports.TableName:
        """Наименование таблицы."""
        return self._name
