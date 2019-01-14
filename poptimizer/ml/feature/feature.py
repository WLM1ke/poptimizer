"""Абстрактный класс признака для машинного обучения."""
from abc import ABC, abstractmethod
from typing import Tuple

import pandas as pd
from hyperopt import hp


def check_bounds(name, days, interval, bound: float = 0.1, increase: float = 0.2):
    """Предложение по расширению интервала"""
    lower, upper = interval
    if days / (1 + bound) < lower:
        print(
            f"\nНеобходимо расширить {name} до [{days / (1 + increase):.0f}, {upper}]"
        )
    elif days * (1 + bound) > upper:
        print(
            f"\nНеобходимо расширить {name} до [{lower}, {days * (1 + increase):.0f}]"
        )


class AbstractFeature(ABC):
    """Создает признак для заданного набора тикеров с использованием статистики до определенной даты."""

    def __init__(self, tickers: Tuple[str, ...], last_date: pd.Timestamp):
        """При конкретной реализации целесообразно так же сохранить данные, необходимые для генерации
        значений на конкретные даты."""
        self._tickers = tickers
        self._last_date = last_date

    @property
    def name(self):
        """Наименование признака."""
        return self.__class__.__name__

    @staticmethod
    @abstractmethod
    def is_categorical() -> bool:
        """Должен возвращать True для категориальных признаков."""

    @classmethod
    @abstractmethod
    def get_params_space(cls) -> dict:
        """Вероятностное пространство параметров признака.

        Словарь с описанием допустимых значений параметров метода set_params в формате hyperopt.
        """

    @abstractmethod
    def check_bounds(self, **kwargs):
        """Проверяет, насколько параметры близки к границам вероятностного пространства.

        При необходимости печатает рекомендации по его расширению.
        """

    @abstractmethod
    def get(self, date: pd.Timestamp, **kwargs) -> pd.Series:
        """Создает признак для заданных тикеров на указанную дату с учетом параметров.

        Признак должен быть pd.Series с индексом из тикеров.
        """


class DaysParamsMixin:
    """Класс с реализацией параметра с количеством дней для признака."""

    # Диапазон допустимого количества дней
    RANGE = [None, None]

    @staticmethod
    def is_categorical() -> bool:
        """Не категориальный признак."""
        return False

    @classmethod
    def get_params_space(cls) -> dict:
        """Значение дней в диапазоне."""
        return {"days": hp.choice("label_days", list(range(*cls.RANGE)))}

    def check_bounds(self, **kwargs):
        """Рекомендация по расширению интервала."""
        days = kwargs["days"]
        check_bounds(f"{self.__class__.__name__}_RANGE", days, self.RANGE)
