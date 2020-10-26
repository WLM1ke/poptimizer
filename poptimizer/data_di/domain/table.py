"""Основной объект доменной модели - таблица."""
import abc
import asyncio
from datetime import datetime
from typing import Generic, List, Optional, TypeVar, Union

import pandas as pd

from poptimizer.data_di.shared import events
from poptimizer.data_di.shared import entity

# Наименование пакета по сбору таблиц
PACKAGE = "data"


class TableID(entity.BaseID):
    """Идентификатор таблиц."""

    def __init__(self, group: str, name: str):
        """Инициализирует базовый класс."""
        super().__init__(PACKAGE, group, name)


TableAttrValues = Union[pd.DataFrame, datetime]
Event = TypeVar("Event", bound=events.AbstractEvent)


class BaseTable(Generic[Event], entity.BaseEntity[TableAttrValues]):
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

    async def handle_event(self, event: Event) -> None:
        """Обновляет значение, изменяет текущую дату и добавляет связанные с этим события."""
        async with self._df_lock:
            if self._update_cond(event):
                df_new = await self._prepare_df(event)

                self._validate_data_and_index(df_new)

                self._timestamp = datetime.utcnow()
                self._df = df_new
                self._events.extend(self._new_events())

    @abc.abstractmethod
    def _update_cond(self, event: Event) -> bool:
        """Условие обновления."""

    @abc.abstractmethod
    async def _prepare_df(self, event: Event) -> pd.DataFrame:
        """Новое значение DataFrame."""

    @abc.abstractmethod
    def _validate_data_and_index(self, df_new: pd.DataFrame) -> None:
        """Проверка корректности новых данных в сравнении со старыми."""

    @abc.abstractmethod
    def _new_events(self) -> List[events.AbstractEvent]:
        """События, которые нужно создать по результатам обновления."""
        return []
