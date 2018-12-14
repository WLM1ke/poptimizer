"""Абстрактный класс признака для машинного обучения."""
from abc import ABC, abstractmethod
from typing import Tuple

import pandas as pd


class AbstractFeature(ABC):
    """Создает признак для заданного набора тикеров с использованием статистики до определенной даты."""

    def __init__(self, tickers: Tuple[str], last_date: pd.Timestamp):
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
