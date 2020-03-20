"""Абстрактный класс признака для машинного обучения."""
from abc import ABC, abstractmethod
from typing import Tuple, List

import pandas as pd
from hyperopt import hp

# Относительная ширина относительно базового значения для вероятностного пространства
SPACE_RANGE = 0.1
ON_OFF = "on_off"


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

    @property
    def col_names(self):
        """Наименование колонок признака."""
        return [self.__class__.__name__]

    @staticmethod
    @abstractmethod
    def is_categorical(param) -> List[bool]:
        """Должен возвращать [True] для категориальных признаков.

        Если признак разбит на несколько, то количество элементов должно соответствовать количеству
        подпризнаков.
        """

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


def days_choice_list(days, space_range=SPACE_RANGE) -> List[int, ...]:
    """Список дней в окрестности указанного значения."""
    return list(range(int(days * (1 - space_range)), int(days * (1 + space_range)) + 2))


# noinspection PyUnresolvedReferences
class DaysParamsMixin:
    """Класс с реализацией параметра с количеством дней для признака."""

    @staticmethod
    def is_categorical(_) -> List[bool]:
        """Не категориальный признак."""
        return [False]

    def get_params_space(self) -> dict:
        """Значение дней в диапазоне."""
        days = self._params["days"]
        return {
            ON_OFF: True,
            "days": hp.choice(f"{self.name}_DAYS", days_choice_list(days)),
        }


def periods_choice_list(periods) -> List[int, ...]:
    """Значение периодов в диапазоне от 1 до текущего + 1."""
    return list(range(1, periods + 2))


class DaysPeriodsParamsMixin:
    """Класс с реализацией параметра с количеством дней для признака и количества периодов."""

    # noinspection PyUnresolvedReferences
    @property
    def col_names(self):
        """Наименование признака."""
        periods = self._params["periods"]
        return [f"{self.__class__.__name__}_{i}" for i in range(periods)]

    @staticmethod
    def is_categorical(params) -> List[bool]:
        """Не категориальный признак."""
        periods = params["periods"]
        return [False] * periods

    # noinspection PyUnresolvedReferences
    def get_params_space(self) -> dict:
        """Значение дней в диапазоне."""
        days = self._params["days"]
        periods = self._params["periods"]
        return {
            ON_OFF: True,
            "days": hp.choice(f"{self.name}_DAYS", days_choice_list(days)),
            "periods": hp.choice(f"{self.name}_PERIODS", periods_choice_list(periods)),
        }


# noinspection PyUnresolvedReferences
class DaysParamsOffMixin:
    """Класс с реализацией параметра с количеством дней для признака и возможность отключения."""

    @staticmethod
    def is_categorical(_) -> List[bool]:
        """Не категориальный признак."""
        return [False]

    def get_params_space(self) -> dict:
        """Значение дней в диапазоне и включение/отключение признака."""
        days = self._params["days"]
        return {
            ON_OFF: hp.choice(f"{self.name}_ON_OFF", [True, False]),
            "days": hp.choice(f"{self.name}_DAYS", days_choice_list(days)),
        }
