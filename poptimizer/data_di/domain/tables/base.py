"""Основной объект доменной модели - таблица."""
import abc
import asyncio
from datetime import datetime
from typing import ClassVar, Final, Generic, List, Literal, Optional, TypeVar

import pandas as pd

from poptimizer import config
from poptimizer.data_di.shared import domain

PACKAGE = "data"


def create_id(group: str, name: Optional[str] = None) -> domain.ID:
    """Создает ID таблицы."""
    if name is None:
        name = group
    return domain.ID(PACKAGE, group, name)


class WrongTableIDError(config.POptimizerError):
    """Не соответствие группы таблицы и ее класса."""


class TableNewDataMismatchError(config.POptimizerError):
    """Новые данные не соответствуют старым данным таблицы."""


class TableIndexError(config.POptimizerError):
    """Ошибка в индексе таблицы."""


class TableNeverUpdatedError(config.POptimizerError):
    """Недопустимая операция с не обновленной таблицей."""


Event = TypeVar("Event", bound=domain.AbstractEvent)

# Наименования групп таблиц
TRADING_DATES: Final = "trading_dates"
CONOMY: Final = "conomy"
DOHOD: Final = "dohod"
SMART_LAB: Final = "smart_lab"
BCS: Final = "bcs"
DIVIDENDS: Final = "dividends"
CPI: Final = "CPI"
SECURITIES: Final = "securities"
INDEX: Final = "indexes"
QUOTES: Final = "quotes"

GroupName = Literal[
    "trading_dates",
    "conomy",
    "dohod",
    "smart_lab",
    "bcs",
    "dividends",
    "CPI",
    "securities",
    "MCFTRR",
    "quotes",
]


class AbstractTable(Generic[Event], domain.BaseEntity):
    """Базовая таблица.

    Хранит время последнего обновления и DataFrame.
    Умеет обрабатывать связанное с ней событие.
    """

    group: ClassVar[GroupName]

    def __init__(
        self,
        id_: domain.ID,
        df: Optional[pd.DataFrame] = None,
        timestamp: Optional[datetime] = None,
    ) -> None:
        """Сохраняет необходимые данные."""
        if id_.package != PACKAGE:
            raise WrongTableIDError(id_)
        if id_.group != self.group:
            raise WrongTableIDError(id_)
        super().__init__(id_)

        self._df = df
        self._timestamp = timestamp
        self._df_lock = asyncio.Lock()

    async def handle_event(self, event: Event) -> List[domain.AbstractEvent]:
        """Обновляет значение, изменяет текущую дату и добавляет связанные с этим события."""
        async with self._df_lock:
            if self._update_cond(event):
                df_new = await self._prepare_df(event)

                self._validate_new_df(df_new)

                self._timestamp = datetime.utcnow()
                self._df = df_new
                return self._new_events(event)
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
    def _new_events(self, event: Event) -> List[domain.AbstractEvent]:
        """События, которые нужно создать по результатам обновления."""


def check_unique_increasing_index(df: pd.DataFrame) -> None:
    """Тестирует индекс на уникальность и возрастание."""
    index = df.index
    if not index.is_monotonic_increasing:
        raise TableIndexError("Индекс не возрастающий")
    if not index.is_unique:
        raise TableIndexError("Индекс не уникальный")
