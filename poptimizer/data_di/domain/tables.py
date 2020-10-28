"""Основной объект доменной модели - таблица."""
import abc
import asyncio
import dataclasses
from datetime import datetime
from typing import Final, Generic, List, Optional, TypeVar

import pandas as pd

from poptimizer import config
from poptimizer.data_di.shared import entity
from poptimizer.data_di.shared.entity import AbstractEvent, ID

# Наименование корневого пакета всех таблиц
TABLES_PACKAGE: Final = "data"


class TableNewDataMismatchError(config.POptimizerError):
    """Новые данные не соответствуют старым данным таблицы."""


class TableIndexError(config.POptimizerError):
    """Ошибка в индексе таблицы."""


class TableNeverUpdatedError(config.POptimizerError):
    """Недопустимая операция с не обновленной таблицей."""


@dataclasses.dataclass(frozen=True)
class TableID(ID):
    """ID таблицы - с фиксированным наименованием пакета."""

    package: str = dataclasses.field(default=TABLES_PACKAGE, init=False)


Event = TypeVar("Event", bound=AbstractEvent)


class AbstractTable(Generic[Event], entity.BaseEntity):
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

                self._validate_new_df(df_new)

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
    def _validate_new_df(self, df_new: pd.DataFrame) -> None:
        """Проверка корректности новых данных в сравнении со старыми."""

    @abc.abstractmethod
    def _new_events(self) -> List[AbstractEvent]:
        """События, которые нужно создать по результатам обновления."""
