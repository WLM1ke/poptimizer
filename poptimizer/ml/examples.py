"""Набор обучающих примеров."""
from typing import Tuple

import pandas as pd

from poptimizer.ml.feature.divyield import DivYield
from poptimizer.ml.feature.label import Label
from poptimizer.ml.feature.mom12 import Mom12m
from poptimizer.ml.feature.mom1m import Mom1m
from poptimizer.ml.feature.retmax import RetMax
from poptimizer.ml.feature.std import STD
from poptimizer.ml.feature.ticker import Ticker

TRAIN_VAL_SPLIT = 0.9

ML_PARAMS = (
    (
        (Label, {"days": 21}),
        (STD, {"on_off": True, "days": 20}),
        (Ticker, {"on_off": True}),
        (Mom12m, {"on_off": True, "days": 251}),
        (DivYield, {"on_off": True, "days": 253}),
        (Mom1m, {"on_off": True, "days": 21}),
        (RetMax, {"on_off": True, "days": 22}),
    ),
    {
        "bagging_temperature": 1.041_367_726_420_619,
        "depth": 5,
        "l2_leaf_reg": 2.764_496_778_258_427_3,
        "learning_rate": 0.060_435_197_338_608_936,
        "one_hot_max_size": 100,
        "random_strength": 1.376_092_249_675_814_1,
        "ignored_features": [],
    },
)


class Examples:
    """Позволяет сформировать набор обучающих примеров и меток к ним.

    Разбить данные на обучающую и валидирующую выборку или получить полный набор данных.
    """

    # noinspection PyUnresolvedReferences
    def __init__(self, tickers: Tuple[str, ...], date: pd.Timestamp, params: tuple):
        """Обучающие примеры состоят из признаков на основе данных для тикеров до указанной даты.

        :param tickers:
            Тикеры, для которых нужно составить обучающие примеры.
        :param date:
            Последняя дата, до которой можно использовать данные.
        :param params:
            Параметры признаков ML-модели.
        """
        self._tickers = tickers
        self._date = date
        self._params = [feat_params for cls, feat_params in params]
        self._features = [
            cls(tickers, date, feat_params) for cls, feat_params in params
        ]

    def get_features_names(self):
        """Название признаков."""
        return [feat.name for feat in self._features[1:]]

    def categorical_features(self):
        """Массив с указанием номеров признаков с категориальными данными."""
        return [n for n, feat in enumerate(self._features[1:]) if feat.is_categorical()]

    def get_params_space(self):
        """Формирует общее вероятностное пространство модели."""
        return [feat.get_params_space() for feat in self._features]

    def get_all(self, params):
        """Получить все обучающие примеры.

        Значение признаков создается в том числе для не используемых признаков.
        Метки нормируются по СКО.
        """
        data = [
            feat.get(feat_params) for feat, feat_params in zip(self._features, params)
        ]
        data[0] /= data[1]
        data = pd.concat(data, axis=1)
        return data

    def train_val_pool_params(self, params=None):
        """Данные для создание catboost.Pool с обучающими и валидационными примерами."""
        params = params or self._params
        df = self.get_all(params).dropna(axis=0)
        dates = df.index.get_level_values(0)
        val_start = dates[int(len(dates) * TRAIN_VAL_SPLIT)]
        df_val = df[dates >= val_start]
        params = params or self._params
        label_days = params[0]["days"]
        train_end = dates[dates < val_start].unique()[-label_days]
        df_train = df.loc[dates <= train_end]
        train_params = dict(
            data=df_train.iloc[:, 1:],
            label=df_train.iloc[:, 0],
            cat_features=self.categorical_features(),
            feature_names=list(df.columns[1:]),
        )
        val_params = dict(
            data=df_val.iloc[:, 1:],
            label=df_val.iloc[:, 0],
            cat_features=self.categorical_features(),
            feature_names=list(df.columns[1:]),
        )
        return train_params, val_params

    def train_predict_pool_params(self):
        """Данные для создание catboost.Pool с примерами для прогноза."""
        df = self.get_all(self._params)
        dates = df.index.get_level_values(0)
        df_predict = df.loc[dates == self._date]
        predict_params = dict(
            data=df_predict.iloc[:, 1:],
            label=None,
            cat_features=self.categorical_features(),
            feature_names=list(df.columns[1:]),
        )
        df = df.dropna(axis=0)
        train_params = dict(
            data=df.iloc[:, 1:],
            label=df.iloc[:, 0],
            cat_features=self.categorical_features(),
            feature_names=list(df.columns[1:]),
        )
        return train_params, predict_params
