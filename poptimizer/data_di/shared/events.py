"""Доменные события и их обработчики."""
import abc
import dataclasses
from typing import Generic, TypeVar


@dataclasses.dataclass(frozen=True)
class AbstractEvent(abc.ABC):
    """Абстрактный тип события."""


Event = TypeVar("Event", bound=AbstractEvent)


class AbstractHandler(Generic[Event], abc.ABC):
    """Абстрактный тип обработчика событий."""

    @abc.abstractmethod
    def handle_event(self, event: Event) -> None:
        """Обрабатывает событие."""
