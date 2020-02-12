"""Абстрактный класс признака."""
from abc import ABC, abstractmethod
from typing import Tuple, Optional

import pandas as pd
from torch import Tensor

from poptimizer import data

# Параметры формирования примеров для обучения сетей
PARAMS = {
    "history_days": 252,
    "Label": {"days": 4, "div_share": 0.7},
    "Prices": {},
    "Dividends": {},
    "Weight": {},
}


class ModelParams(object):
    """Параметры модели."""

    def __init__(
        self,
        tickers: Tuple[str, ...],
        start: Optional[pd.Timestamp],
        end: pd.Timestamp,
        params: dict,
    ):
        """Модель строится для определенного набора тикеров и диапазона дат с использованием
        различного набора параметров.

        :param tickers:
            Перечень тикеров, для которых будет строится модель.
        :param start:
            Начало диапазона дат статистики по ценам и дивидендам, которые будут использоваться для
            построения модели. Может отсутствовать, тогда будет использоваться данные с начала
            исторических котировок.
        :param end:
            Конец диапазона дат статистики по ценам и дивидендам, которые будут использоваться для
            построения модели.
        :param params:
            Словарь с параметрами для построения признаков и других элементов модели.
        """
        div, price = data.div_ex_date_prices(tickers, end)
        div = div.loc[start:]
        price = price.loc[start:]
        self._div = dict()
        self._price = dict()
        for ticker in tickers:
            start = price[ticker].first_valid_index()
            self._div[ticker] = div.loc[start:, ticker]
            self._price[ticker] = price.loc[start:, ticker]
        self._params = params

    @property
    def forecast_days(self) -> Optional[int]:
        """Длинна меток в днях."""
        label = self._params.get("Label")
        return label and label["days"]

    @property
    def history_days(self):
        """Длинна истории для признаков в днях."""
        return self._params["history_days"]

    def price(self, ticker: str) -> pd.Series:
        """Цены для тикера и диапазона дат, которых будут использоваться для построения признаков,
        с учетом возможного отсутствия котировок в начале."""
        return self._price[ticker]

    def div(self, ticker: str) -> pd.Series:
        """Дивиденды для тикера и диапазона дат, которых будут использоваться для построения
        признаков, с учетом возможного отсутствия котировок в начале."""
        return self._div[ticker]

    def __getitem__(self, feat_name: str):
        return self._params[feat_name]


class Feature(ABC):
    """Абстрактный класс признака."""

    def __init__(self, ticker: str, params: ModelParams):
        pass

    @abstractmethod
    def __getitem__(self, item: int) -> Tensor:
        pass

    @property
    def name(self) -> str:
        """Наименование признака."""
        return self.__class__.__name__
