"""Основной объект доменной модели - таблица."""
import abc
import asyncio
import weakref
from datetime import datetime
from typing import ClassVar, Generic, List, MutableMapping, Optional, Set, TypeVar

import pandas as pd

from poptimizer import config
from poptimizer.data_di.shared import entities, mapper

PACKAGE = "data"


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

    _group: ClassVar[str]

    def create_table(
        self,
        table_id: entities.ID,
        df: Optional[pd.DataFrame] = None,
        timestamp: Optional[datetime] = None,
    ) -> AbstractTable[Event]:
        """Создает таблицу определенного типа и проверяет корректность группы таблицы."""
        if table_id.package != PACKAGE:
            raise WrongTableIDError(table_id)
        if table_id.group != self._group:
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


class Repo(Generic[Event]):
    """Класс репозитория для хранения таблиц.

    Контекстный менеджер обеспечивающий сохранение измененных таблиц. С помощью identity_map
    обеспечивается корректная обработка запроса одной и той же таблицы из разных репо при их
    асинхронной обработке.
    """

    _identity_map: MutableMapping[
        entities.ID,
        AbstractTable[Event],
    ] = weakref.WeakValueDictionary()

    def __init__(
        self,
        db_session: mapper.MongoDBSession,
        factory: AbstractTableFactory[Event],
    ) -> None:
        """Сохраняются ссылки на таблицы, которые были добавлены или взяты из репозитория."""
        self._session = db_session
        self._factory = factory
        self._seen: Set[AbstractTable[Event]] = set()

    def seen(self) -> Set[AbstractTable[Event]]:
        """Возвращает виденные таблицы."""
        return self._seen

    async def get_table(self, table_id: entities.ID) -> AbstractTable[Event]:
        """Берет таблицу из репозитория."""
        table = await self._load_table(table_id)
        self._seen.add(table)
        return table

    async def _load_table(self, table_id: entities.ID) -> AbstractTable[Event]:
        """Загрузка таблицы.

        - Синхронно загружается из identity map
        - Если отсутствует, то асинхронно загружается из базы или создается новая
        - Из-за асинхронности снова проверяется наличие в identity map
        - При отсутствии происходит обновление identity map
        """
        if (table_old := self._identity_map.get(table_id)) is not None:
            return table_old

        table = await self._load_or_create(table_id)

        if (table_old := self._identity_map.get(table_id)) is not None:
            return table_old

        self._identity_map[table_id] = table

        return table

    async def _load_or_create(self, table_id: entities.ID) -> AbstractTable[Event]:
        """Загружает из базы, а в случае отсутствия создается пустая таблица."""
        if (doc := await self._session.get(table_id)) is None:
            doc = {}
        return self._factory.create_table(table_id, **doc)
