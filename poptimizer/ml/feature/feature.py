"""Абстрактный класс признака для машинного обучения."""
from abc import ABC, abstractmethod
from typing import Tuple

import pandas as pd
from hyperopt import hp

# Относительная ширина относительно базового значения для вероятностного пространства
SPACE_RANGE = 0.1


class AbstractFeature(ABC):
    """Создает признак для заданного набора тикеров с использованием статистики до определенной даты."""

    def __init__(self, tickers: Tuple[str, ...], last_date: pd.Timestamp, params: dict):
        """При конкретной реализации целесообразно так же сохранить данные, необходимые для генерации
        значений на конкретные даты."""
        self._tickers = tickers
        self._last_date = last_date
        self._params = params

    @property
    def name(self):
        """Наименование признака."""
        return self.__class__.__name__

    @staticmethod
    @abstractmethod
    def is_categorical() -> bool:
        """Должен возвращать True для категориальных признаков."""

    @abstractmethod
    def get_params_space(self) -> dict:
        """Вероятностное пространство параметров признака.

        Словарь с описанием допустимых значений параметров в формате hyperopt.
        """

    @abstractmethod
    def get(self, params=None) -> pd.Series:
        """Создает признак для заданных тикеров на указанную дату с учетом параметров.

        Признак должен быть pd.Series с индексом (дата, тикер).
        """


def choice_list(days, space_range=SPACE_RANGE):
    """Список дней в окрестности указанного значения."""
    return list(range(int(days * (1 - space_range)), int(days * (1 + space_range)) + 2))


# noinspection PyUnresolvedReferences
class DaysParamsMixin:
    """Класс с реализацией параметра с количеством дней для признака."""

    @staticmethod
    def is_categorical() -> bool:
        """Не категориальный признак."""
        return False

    def get_params_space(self) -> dict:
        """Значение дней в диапазоне."""
        days = self._params["days"]
        return {
            "on_off": True,
            "days": hp.choice(f"{self.name}_DAYS", choice_list(days)),
        }
