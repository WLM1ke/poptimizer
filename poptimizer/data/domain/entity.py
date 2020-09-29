"""Базовый класс сущности."""
from typing import TypeVar

AttrValues = TypeVar("AttrValues")


class BaseEntity:
    """Базовый класс сущности.

    Записывает измененные поля и может их сбрасывать.
    """

    def __init__(self) -> None:
        """Хранит словарь изменных полей."""
        self._dirty = False

    def __setattr__(self, key: str, attr_value: AttrValues) -> None:
        """Сохраняет изменное значение."""
        if key in vars(self) and not self._dirty:  # noqa: WPS421
            super().__setattr__("_dirty", True)  # noqa: WPS425
        super().__setattr__(key, attr_value)

    def clear(self) -> None:
        """Сбрасывает перечень изменных полей."""
        self._dirty = False

    def is_dirty(self) -> bool:
        """Возвращает view на изменные поля."""
        return self._dirty
