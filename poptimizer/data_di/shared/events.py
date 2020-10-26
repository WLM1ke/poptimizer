"""Доменные события и их обработчики."""
import abc
from typing import Generic, TypeVar


class AbstractEvent(abc.ABC):
    """Абстрактный тип события."""


Event = TypeVar("Event", bound=AbstractEvent)


class AbstractHandler(Generic[Event], abc.ABC):
    """Абстрактный тип обработчика событий."""

    @abc.abstractmethod
    def handle_event(self, event: Event) -> None:
        """Обрабатывает событие."""
