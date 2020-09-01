"""Абстрактный класс события."""
import abc
from typing import Dict, List, Tuple

from poptimizer.data.domain import model
from poptimizer.data.ports import base


class AbstractEvent(abc.ABC):
    """Абстрактный класс события."""

    def __init__(self) -> None:
        """Создает список для хранения последующих события."""
        self._new_events: List["AbstractEvent"] = []

    @property
    def tables_required(self) -> Tuple[base.TableName, ...]:
        """Перечень таблиц, которые нужны обработчику события."""
        return ()

    @abc.abstractmethod
    def handle_event(self, tables_dict: Dict[base.TableName, model.Table]) -> None:
        """Обрабатывает событие."""

    @property
    def new_events(self) -> List["AbstractEvent"]:
        """События, которые появились во время обработки сообщения."""
        return self._new_events
