"""Абстрактный класс признака для машинного обучения."""
from abc import ABC, abstractmethod
from typing import List

import pandas as pd


class AbstractFeature(ABC):
    """Создает признак для заданного набора тикеров с использованием статистики до заданной даты."""

    def __init__(self, tickers: List[str], date: pd.Timestamp):
        self._tickers = tickers
        self._date = date

    @abstractmethod
    def get_feature(self, *kwargs) -> pd.DataFrame:
        """Создает признак для заданного значения параметров.

        У каждого признака могут быть свои параметры, а могут и отсутствовать.
        Признак должен быть pd.DataFrame с многоуровневым индексом:

            * Первый уровень - дата
            * Второй уровень - тикер
        """

    @staticmethod
    @abstractmethod
    def is_categorical(self) -> bool:
        """Должен возвращать True для категориальных признаков."""

    @abstractmethod
    def get_param_space(self) -> dict:
        """Вероятностное пространство параметров признака.

        Словарь с описанием допустимых значений параметров метода get_feature в формате hyperopt.
        """

    @abstractmethod
    def check_bounds(self, *kwargs):
        """Проверяет, насколько параметры близки к границам вероятностного пространства.

        При необходимости печатает рекомендации по его расширению.
        """
