"""Основной объект доменной модели - таблица."""
import abc
import asyncio
from datetime import datetime
from typing import ClassVar, Generic, List, Optional, TypeVar

import pandas as pd

from poptimizer import config
from poptimizer.data_di.shared import entities

PACKAGE = "data"


def create_id(group: str, name: Optional[str] = None) -> entities.ID:
    """Создает ID таблицы."""
    if name is None:
        name = group
    return entities.ID(PACKAGE, group, name)


class TableNewDataMismatchError(config.POptimizerError):
    """Новые данные не соответствуют старым данным таблицы."""


class TableIndexError(config.POptimizerError):
    """Ошибка в индексе таблицы."""


class TableNeverUpdatedError(config.POptimizerError):
    """Недопустимая операция с не обновленной таблицей."""


Event = TypeVar("Event", bound=entities.AbstractEvent)


class AbstractTable(Generic[Event], entities.BaseEntity):
    """Базовая таблица.

    Хранит время последнего обновления и DataFrame.
    Умеет обрабатывать связанное с ней событие.
    """

    def __init__(
        self,
        id_: entities.ID,
        df: Optional[pd.DataFrame],
        timestamp: Optional[datetime],
    ) -> None:
        """Сохраняет необходимые данные."""
        super().__init__(id_)
        self._df = df
        self._timestamp = timestamp
        self._df_lock = asyncio.Lock()

    async def handle_event(self, event: Event) -> List[entities.AbstractEvent]:
        """Обновляет значение, изменяет текущую дату и добавляет связанные с этим события."""
        async with self._df_lock:
            if self._update_cond(event):
                df_new = await self._prepare_df(event)

                self._validate_new_df(df_new)

                self._timestamp = datetime.utcnow()
                self._df = df_new
                return self._new_events()
            return []

    @abc.abstractmethod
    def _update_cond(self, event: Event) -> bool:
        """Условие обновления."""

    @abc.abstractmethod
    async def _prepare_df(self, event: Event) -> pd.DataFrame:
        """Новое значение DataFrame."""

    @abc.abstractmethod
    def _validate_new_df(self, df_new: pd.DataFrame) -> None:
        """Проверка корректности новых данных в сравнении со старыми."""

    @abc.abstractmethod
    def _new_events(self) -> List[entities.AbstractEvent]:
        """События, которые нужно создать по результатам обновления."""


class WrongTableIDError(config.POptimizerError):
    """Не соответствие группы таблицы и ее класса."""


class AbstractTableFactory(Generic[Event], abc.ABC):
    """Фабрика по созданию таблиц определенного типа."""

    group: ClassVar[str]

    def create_table(
        self,
        table_id: entities.ID,
        df: Optional[pd.DataFrame] = None,
        timestamp: Optional[datetime] = None,
    ) -> AbstractTable[Event]:
        """Создает таблицу определенного типа и проверяет корректность группы таблицы."""
        if table_id.package != PACKAGE:
            raise WrongTableIDError(table_id)
        if table_id.group != self.group:
            raise WrongTableIDError(table_id)
        return self._create_table(table_id, df, timestamp)

    @abc.abstractmethod
    def _create_table(
        self,
        table_id: entities.ID,
        df: Optional[pd.DataFrame] = None,
        timestamp: Optional[datetime] = None,
    ) -> AbstractTable[Event]:
        """Создает таблицу определенного типа."""
