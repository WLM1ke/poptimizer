"""Обучающие примеры для обучения, валидации и тестирования."""
from typing import Tuple, Optional

import pandas as pd
from torch.utils.data import Dataset

from poptimizer import data
from poptimizer.dl import datasets
from poptimizer.ml.examples import TRAIN_VAL_SPLIT

# Параметры формирования примеров для обучения сетей
DL_PARAMS = {"history_days": 264, "forecast_days": 341, "div_share": 0.6}


class Examples:
    """Позволяет сформировать набор примеров и меток к ним.

    Поддерживаются следующие пары наборов примеров:

    - Обучение и валидация для подбора гиперпараметров.
    - Обучение и прогнозирование.
    """

    def __init__(self, tickers: Tuple[str, ...], date: pd.Timestamp, params: dict):
        """Обучающие примеры состоят из признаков на основе данных для тикеров до указанной даты.

        :param tickers:
            Тикеры, для которых нужно составить обучающие примеры.
        :param date:
            Последняя дата, до которой можно использовать данные.
        :param params:
            Параметры признаков ML-модели.
        """
        self.div, self.price = data.div_ex_date_prices(tickers, date)
        self._params = params

    def train_val_dataset(
        self, params: Optional[dict] = None
    ) -> Tuple[Dataset, Dataset]:
        """Данные для обучения и валидации модели.

        :param params:
            Параметры для создания признаков.
        :return:
            Два набора данных - для обучения и валидации. Между данными есть некоторый зазор,
            чтобы метки не пересекались даже частично.
        """
        params = params or self._params
        price = self.price
        div = self.div

        history_days = params["history_days"]
        forecast_days = params["forecast_days"]
        dates = price.index[:-forecast_days]
        val_start = history_days + int((len(dates) - history_days) * TRAIN_VAL_SPLIT)
        return (
            datasets.get_dataset(
                price,
                div,
                params,
                None,
                dates[val_start + history_days - 1 - forecast_days],
            ),
            datasets.get_dataset(price, div, params, dates[val_start], dates[-1]),
        )

    def train_predict_dataset(self) -> Tuple[Dataset, Dataset]:
        """Данные для обучения и окончательного прогноза.

        :return:
            Два набора данных - для обучения и предсказания. Данные для обучения охватывают весь
            диапазон дат, для которых может быть сформирована метка. Для предсказания используются
            последняя дата для каждого тикера, для которой можно сформировать признаки.
        """
        params = self._params
        price = self.price
        div = self.div
        dates = price.index

        forecast_days = params["forecast_days"]
        history_days = params["history_days"]
        return (
            datasets.get_dataset(price, div, params, None, dates[-1 - forecast_days]),
            datasets.get_dataset(price, div, params, dates[-history_days], None),
        )
