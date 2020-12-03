"""Базовые классы доменной области."""
import abc
import dataclasses
from typing import Dict, Generic, List, TypeVar


@dataclasses.dataclass(frozen=True)
class AbstractEvent(abc.ABC):
    """Абстрактный тип события."""


@dataclasses.dataclass(frozen=True)
class ID:
    """Базовый идентификатор доменного объекта."""

    package: str
    group: str
    name: str


StateDict = Dict[str, object]


class BaseEntity:
    """Абстрактный класс сущности.

    Обязательно имеет поле с идентификатором и автоматическим отслеживанием статуса изменений.
    """

    def __init__(self, id_: ID) -> None:
        """Сохраняет ID и словарь изменений."""
        self._id = id_
        self._changed_state: StateDict = {}

    def __setattr__(self, key: str, attr_value: object) -> None:
        """Сохраняет изменное значение."""
        if key in vars(self):  # noqa: WPS421
            self._changed_state[key] = attr_value
        super().__setattr__(key, attr_value)

    @property
    def id_(self) -> ID:
        """Уникальный идентификатор доменного объекта."""
        return self._id

    def changed_state(self) -> StateDict:
        """Показывает измененные атрибуты."""
        return self._changed_state.copy()

    def clear(self) -> None:
        """Сбрасывает изменения."""
        self._changed_state.clear()


EntityType = TypeVar("EntityType", bound=BaseEntity)


class AbstractFactory(Generic[EntityType], abc.ABC):
    """Абстрактная фабрика по созданию доменных объектов."""

    @abc.abstractmethod
    def __call__(self, id_: ID, mongo_dict: StateDict) -> EntityType:
        """Создает доменные объекты."""


class AbstractRepo(Generic[EntityType], abc.ABC):
    """Абстрактный репозиторий."""

    @abc.abstractmethod
    async def get(self, id_: ID) -> EntityType:
        """Получить доменный объект по ID."""


class AbstractHandler(Generic[EntityType], abc.ABC):
    """Абстрактный тип обработчика событий."""

    @abc.abstractmethod
    async def handle_event(
        self,
        event: AbstractEvent,
        repo: AbstractRepo[EntityType],
    ) -> List[AbstractEvent]:
        """Обрабатывает событие и возвращает список новых порожденных событий."""
