"""Базовые классы доменных событий и объектов."""
import abc
import dataclasses
from typing import Any, Dict, Generic, Iterator, List, TypeVar


@dataclasses.dataclass(frozen=True)
class AbstractEvent(abc.ABC):
    """Абстрактный тип события."""


Event = TypeVar("Event", bound=AbstractEvent)


class AbstractHandler(Generic[Event], abc.ABC):
    """Абстрактный тип обработчика событий."""

    @abc.abstractmethod
    async def handle_event(self, event: Event) -> None:
        """Обрабатывает событие."""


@dataclasses.dataclass(frozen=True)
class ID:
    """Базовый идентификатор доменного сущности."""

    package: str
    group: str
    name: str


StateDict = Dict[str, Any]  # type: ignore


class BaseEntity:
    """Абстрактный класс сущности.

    Обязательно имеет поле и идентификатором, механизм сохранения и извлечения событий и
    автоматического статуса изменений.
    """

    def __init__(self, id_: ID) -> None:
        """Формирует список событий и отметку об изменениях."""
        self._id = id_
        self._events: List[AbstractEvent] = []
        self._changed_state: StateDict = {}

    def __setattr__(self, key: str, attr_value: Any) -> None:  # type: ignore
        """Сохраняет изменное значение."""
        if key in vars(self):  # noqa: WPS421
            self._changed_state[key] = attr_value
        super().__setattr__(key, attr_value)

    @property
    def id_(self) -> ID:
        """Уникальный идентификатор сущности."""
        return self._id

    def changed_state(self) -> StateDict:
        """Показывает измененные атрибуты."""
        return self._changed_state

    def clear(self) -> None:
        """Сбрасывает изменения."""
        self._changed_state.clear()

    def pop_event(self) -> Iterator[AbstractEvent]:
        """Возвращает события возникшие в за время существования сущности."""
        while self._events:
            yield self._events.pop()
