"""Доменные сущности."""
import abc
import asyncio
from datetime import datetime
from typing import Generic, Iterator, List, Optional, TypeVar

import pandas as pd

from poptimizer.data_di.ports import events

# База данных для хранения информации
DB = "data"

AttrValues = TypeVar("AttrValues")


class BaseID:
    """Базовый идентификатор доменного сущности.

    Реализует необходимую логику для удобства сохранения в MongoDB.
    """

    def __init__(self, db: str, collection: str, _id: str):
        """Сохраняет необходимую информацию."""
        self._db = db
        self._collection = collection
        self._id = _id


class AbstractEntity(abc.ABC):
    """Абстрактный класс сущности.

    Обязательно имеет поле и идентификатором, механизм сохранения и извлечения событий и
    автоматического статуса изменений.
    """

    def __init__(self, id_: BaseID) -> None:
        """Формирует список событий и отметку об изменениях."""
        self._id = id_
        self._events: List[events.AbstractEvent] = []
        self._dirty = False

    def __setattr__(self, key: str, attr_value: AttrValues) -> None:
        """Сохраняет изменное значение."""
        if key in vars(self) and not self._dirty:  # noqa: WPS421
            super().__setattr__("_dirty", True)  # noqa: WPS425
        super().__setattr__(key, attr_value)

    @property
    def id_(self) -> BaseID:
        """Уникальный идентификатор сущности."""
        return self._id

    def clear(self) -> None:
        """Сбрасывает отметку изменения."""
        self._dirty = False

    def is_dirty(self) -> bool:
        """Показывает был ли изменен объект с момента создания."""
        return self._dirty

    def pop_event(self) -> Iterator[events.AbstractEvent]:
        """Возвращает события возникшие в за время существования сущности."""
        while self._events:
            yield self._events.pop()


class TableID(BaseID):
    """Идентификатор таблиц."""

    def __init__(self, group: str, name: str):
        """Инициализирует базовый класс."""
        super().__init__(DB, group, name)


Event = TypeVar("Event", bound=events.AbstractEvent)


class BaseTable(Generic[Event], AbstractEntity):
    """Базовая таблица.

    Хранит время последнего обновления и DataFrame.
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
