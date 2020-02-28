"""Набор обучающих примеров."""
from typing import Optional, Tuple

import pandas as pd

from poptimizer import data
from poptimizer.ml import feature

TRAIN_VAL_SPLIT = 0.9


class Examples:
    """Позволяет сформировать набор обучающих примеров и меток к ним.

    Разбить данные на обучающую и валидирующую выборку или получить полный набор данных.
    """

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
        self._params = params
        self._features = [
            getattr(feature, cls_name)(tickers, date, feat_params)
            for cls_name, feat_params in params
        ]

    @property
    def tickers(self):
        """Используемые тикеры."""
        return self._tickers

    def get_features_names(self) -> list:
        """Название признаков."""
        rez = []
        for feat in self._features[1:]:
            rez.extend(feat.col_names)
        return rez

    def categorical_features(self, params: Optional[tuple] = None) -> list:
        """Массив с указанием номеров признаков с категориальными данными."""
        params = params or self._params
        cat_flag = []
        for feat, (_, feat_param) in zip(self._features[1:], params[1:]):
            cat_flag.extend(feat.is_categorical(feat_param))
        return [n for n, flag in enumerate(cat_flag) if flag]

    def get_params_space(self) -> list:
        """Формирует общее вероятностное пространство модели."""
        return [(feat.name, feat.get_params_space()) for feat in self._features]

    def get_all(self, params: tuple) -> pd.DataFrame:
        """Получить все обучающие примеры.

        Значение признаков создается в том числе для не используемых признаков.
        """
        data = [
            feat.get(feat_params)
            for feat, (_, feat_params) in zip(self._features, params)
        ]
        data = pd.concat(data, axis=1)
        return data

    def train_val_pool_params(
        self, params: Optional[tuple] = None
    ) -> Tuple[dict, dict]:
        """Данные для создание catboost.Pool с обучающими и валидационными примерами.

        Вес у данных обратно пропорционален квадрату СКО - что эквивалентно максимизации функции
        правдоподобия для нормального распределения.
        """
        params = params or self._params

        _, price = data.div_ex_date_prices(self._tickers, self._date)
        val_start_labels = int(len(price) * TRAIN_VAL_SPLIT)
        val_start_labels = price.index[val_start_labels - 1]

        df = self.get_all(params).dropna(axis=0)
        dates = df.index.get_level_values(0)

        df_val = df[dates >= val_start_labels]
        label_days = params[0][1]["days"]
        train_end = dates[dates < val_start_labels].unique()[-label_days]
        df_train = df.loc[dates <= train_end]
        train_params = dict(
            data=df_train.iloc[:, 1:],
            label=df_train.iloc[:, 0],
            weight=1 / df_train.iloc[:, 1] ** 2,
            cat_features=self.categorical_features(params),
            feature_names=list(df.columns[1:]),
        )
        val_params = dict(
            data=df_val.iloc[:, 1:],
            label=df_val.iloc[:, 0],
            weight=1 / df_val.iloc[:, 1] ** 2,
            cat_features=self.categorical_features(params),
            feature_names=list(df.columns[1:]),
        )
        return train_params, val_params

    def train_predict_pool_params(self) -> Tuple[dict, dict]:
        """Данные для создание catboost.Pool с примерами для прогноза.

        Вес у данных обратно пропорционален квадрату СКО - что эквивалентно максимизации функции
        правдоподобия для нормального распределения.
        """
        df = self.get_all(self._params)
        dates = df.index.get_level_values(0)
        df_predict = df.loc[dates == self._date]
        predict_params = dict(
            data=df_predict.iloc[:, 1:],
            label=None,
            weight=1 / df_predict.iloc[:, 1] ** 2,
            cat_features=self.categorical_features(),
            feature_names=list(df.columns[1:]),
        )
        df = df.dropna(axis=0)
        train_params = dict(
            data=df.iloc[:, 1:],
            label=df.iloc[:, 0],
            weight=1 / df.iloc[:, 1] ** 2,
            cat_features=self.categorical_features(),
            feature_names=list(df.columns[1:]),
        )
        return train_params, predict_params
