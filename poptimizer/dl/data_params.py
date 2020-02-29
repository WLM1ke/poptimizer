"""Описание модели и данных."""
import copy
from enum import Enum
from typing import Tuple

import pandas as pd

from poptimizer import data

TRAIN_VAL_SPLIT = 0.9


class DataType(Enum):
    """Тип формируемых данных:

    - TRAIN - используются признаки, как есть для начальной части семпла.
    - VAL - используются признаки, как есть для конечной части семпла, чтобы метки не пересекались с
    TRAIN.
    - TEST - метки имеют длину 1 день в независимости от реального значения параметров для конечной части
    семпла, чтобы метки не пересекались с TRAIN, а вес не формируется.
    - FORECAST - метки и вес не формируются, а признаки формируются только дл я последней даты.
    """

    TRAIN = 1
    VAL = 2
    TEST = 3
    FORECAST = 4


class DataParams(object):
    """Параметры модели."""

    def __init__(
        self,
        tickers: Tuple[str, ...],
        end: pd.Timestamp,
        params: dict,
        feat_type: DataType,
    ):
        """Модель строится для определенного набора тикеров и диапазона дат с использованием
        различного набора параметров.

        :param tickers:
            Перечень тикеров, для которых будет строится модель.
        :param end:
            Конец диапазона дат статистики по ценам и дивидендам, которые будут использоваться для
            построения модели.
        :param params:
            Словарь с параметрами для построения признаков и других элементов модели.
        :param feat_type:
            Тип формируемых признаков.
        """
        div, price = data.div_ex_date_prices(tickers, end)
        self._params = copy.deepcopy(params)
        history_days = self.history_days

        train_size = int(len(price) * TRAIN_VAL_SPLIT)
        if feat_type == DataType.TRAIN:
            div = div.iloc[:train_size]
            price = price.iloc[:train_size]
        elif feat_type == DataType.VAL:
            div = div.iloc[train_size - history_days :]
            price = price.iloc[train_size - history_days :]
        elif feat_type == DataType.TEST:
            div = div.iloc[train_size - history_days :]
            price = price.iloc[train_size - history_days :]
            self._params["forecast_days"] = 1
            del self._params["features"]["Weight"]
        elif feat_type == DataType.FORECAST:
            div = div.iloc[-history_days:]
            price = price.iloc[-history_days:]
            self._params["forecast_days"] = 0
            del self._params["features"]["Label"]
            del self._params["features"]["Weight"]

        self._div = dict()
        self._price = dict()
        for ticker in tickers:
            start = price[ticker].first_valid_index()
            self._div[ticker] = div.loc[start:, ticker]
            self._price[ticker] = price.loc[start:, ticker]

    @property
    def forecast_days(self) -> int:
        """Длинна меток в днях."""
        return self._params["forecast_days"]

    @property
    def history_days(self) -> int:
        """Длинна истории для признаков в днях."""
        return self._params["history_days"]

    @property
    def batch_size(self) -> int:
        """Размер батча."""
        return self._params["batch_size"]

    def price(self, ticker: str) -> pd.Series:
        """Цены для тикера и диапазона дат, которых будут использоваться для построения признаков,
        с учетом возможного отсутствия котировок в начале."""
        return self._price[ticker]

    def div(self, ticker: str) -> pd.Series:
        """Дивиденды для тикера и диапазона дат, которых будут использоваться для построения
        признаков, с учетом возможного отсутствия котировок в начале."""
        return self._div[ticker]

    def len(self, ticker) -> int:
        """Количество доступных примеров для данного тикера."""
        return max(
            0, len(self.price(ticker)) - self.history_days - self.forecast_days + 1
        )

    def get_all_feat(self) -> str:
        """Получить параметры для признака."""
        yield from self._params["features"]

    def get_feat_params(self, feat_name: str) -> dict:
        """Получить параметры для признака."""
        return self._params["features"][feat_name]
