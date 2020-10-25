"""Доменные сущности."""
import abc
from typing import Iterator, List, TypeVar

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


class TableID(BaseID):
    """Идентификатор таблиц."""

    def __init__(self, group: str, name: str):
        """Инициализирует базовый класс."""
        super().__init__(DB, group, name)


class AbstractEntity(abc.ABC):
    """Абстрактный класс сущности.

    Обязательно имеет поле и идентификатором, механизм сохранения и извлечения событий и
    автоматического статуса изменений.
    """

    def __init__(self, _id: BaseID) -> None:
        """Формирует список событий и отметку об изменениях."""
        self._id = _id
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

    def _record_event(self, event: events.AbstractEvent) -> None:
        """Добавляет новое событие."""
        self._events.append(event)
