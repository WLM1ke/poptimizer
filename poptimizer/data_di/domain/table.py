"""Основной объект доменной модели - таблица."""
import abc
import asyncio
from datetime import datetime
from typing import Final, Optional, Union

import pandas as pd

from poptimizer import config
from poptimizer.data_di.shared import entity, events

# Наименование пакета по сбору таблиц
_PACKAGE: Final = "data"


class TableNewDataMismatchError(config.POptimizerError):
    """Новые данные не соответствуют старым данным таблицы."""


class TableIndexError(config.POptimizerError):
    """Ошибка в индексе таблицы."""


class TableNeverUpdatedError(config.POptimizerError):
    """Недопустимая операция с не обновленной таблицей."""


class TableID(entity.BaseID):
    """Идентификатор таблиц."""

    def __init__(self, group: str, name: str):
        """Инициализирует базовый класс."""
        super().__init__(_PACKAGE, group, name)


TableAttrValues = Union[pd.DataFrame, datetime]


class AbstractTable(entity.BaseEntity[TableAttrValues]):
    """Базовая таблица.

    Хранит время последнего обновления и DataFrame.
    Умеет обрабатывать связанное с ней событие.
    Имеет атрибут для получение значения таблицы в виде DataFrame.
    """

    def __init__(
        self,
        id_: TableID,
        df: Optional[pd.DataFrame],
        timestamp: Optional[datetime],
    ) -> None:
        """Сохраняет необходимые данные."""
        super().__init__(id_)
        self._df = df
        self._timestamp = timestamp
        self._df_lock = asyncio.Lock()

    @property
    def df(self) -> Optional[pd.DataFrame]:
        """Таблица с данными."""
        if (df := self._df) is None:
            return None
        return df.copy()

    async def handle_event(self, event: events.AbstractEvent) -> None:
        """Обновляет значение, изменяет текущую дату и добавляет связанные с этим события."""
        async with self._df_lock:
            if self._update_cond(event):
                df_new = await self._prepare_df(event)

                self._validate_new_df(df_new)

                self._timestamp = datetime.utcnow()
                self._df = df_new
                self._events.append(self._new_events())

    @abc.abstractmethod
    def _update_cond(self, event: events.AbstractEvent) -> bool:
        """Условие обновления."""

    @abc.abstractmethod
    async def _prepare_df(self, event: events.AbstractEvent) -> pd.DataFrame:
        """Новое значение DataFrame."""

    @abc.abstractmethod
    def _validate_new_df(self, df_new: pd.DataFrame) -> None:
        """Проверка корректности новых данных в сравнении со старыми."""

    @abc.abstractmethod
    def _new_events(self) -> events.AbstractEvent:
        """События, которые нужно создать по результатам обновления."""
