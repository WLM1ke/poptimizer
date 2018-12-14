"""Набор обучающих примеров."""
from typing import Tuple

import pandas as pd
from hyperopt import hp

from poptimizer.ml import feature

ON_OFF = [True, False]


class Examples:
    """Позволяет сформировать набор обучающих примеров и меток к ним."""

    FEATURES = [
        feature.Label,
        feature.STD,
        feature.Ticker,
        feature.Mean,
        feature.Dividends,
    ]

    def __init__(self, tickers: Tuple[str], last_date: pd.Timestamp):
        """Обучающие примеры состоят из признаков на основе данных для тикеров до указанной даты.

        :param tickers:
            Тикеры, для которых нужно составить обучающие примеры.
        :param last_date:
            Последняя дата, до которой можно использовать данные.
        """
        self._tickers = tickers
        self._last_date = last_date
        self._features = [cls(tickers, last_date) for cls in self.FEATURES]

    def categorical_features(self):
        """Массив с указанием номеров признаков с категориальными данными."""
        return [n for n, feat in enumerate(self._features[1:]) if feat.is_categorical()]

    def get_params_space(self):
        """Формирует общее вероятностное пространство модели.

        Массив из кортежей:

        * первый элемент - используется признак или нет
        * второй элемент - подпространство для параметров признака

        Метка данных включается всегда.
        """
        it = iter(self._features)
        label = next(it)
        space = [(True, label.get_params_space())]
        for feat in it:
            space.append([hp.choice(feat.name, ON_OFF), feat.get_params_space()])
        return space

    def check_bounds(self, params: tuple):
        """Осуществляет проверку близости параметров к границам вероятностного пространства.

        Проверка осуществляется только для используемых признаков.
        """
        for feat, (on_off, value) in zip(self._features, params):
            if on_off:
                feat.check_bounds(**value)

    def get(self, date: pd.Timestamp, params):
        """Получить обучающие примеры для одной даты.

        Значение признаков создается в том числе для не используемых признаков.
        Метки нормируются по СКО.
        """
        data = [
            feat.get(date, **value) for feat, (_, value) in zip(self._features, params)
        ]
        data[0] /= data[1]
        return pd.concat(data, axis=1)

    def learn_pool(self, params):
        """Данные для создание catboost.Pool с обучающими примерами."""
        label = self._features[0]
        days = params[0][1]["days"]
        index = label.index
        loc = index.get_loc(self._last_date)
        index = index[loc - days :: -days]
        data = [self.get(date, params) for date in index]
        df = pd.concat(data, axis=0, ignore_index=True)
        df.dropna(axis=0, inplace=True)
        return dict(
            data=df.iloc[:, 1:],
            label=df.iloc[:, 0],
            cat_features=self.categorical_features(),
            feature_names=list(df.columns[1:]),
        )

    def predict_pool(self, params):
        """Данные для создание catboost.Pool с примерами для прогноза."""
        df = self.get(self._last_date, params)
        return dict(
            data=df.iloc[:, 1:],
            label=None,
            cat_features=self.categorical_features(),
            feature_names=list(df.columns[1:]),
        )
