"""Набор обучающих примеров."""
import pandas as pd
from hyperopt import hp
from typing import Tuple

from poptimizer.config import POptimizerError
from poptimizer.ml import feature

ON_OFF = [True, False]


class Examples:
    """Позволяет сформировать набор обучающих примеров и меток к ним."""

    FEATURES = [
        feature.Label,
        feature.STD,
        feature.Ticker,
        feature.Mom12m,
        feature.DivYield,
        feature.Mom1m,
    ]

    def __init__(self, tickers: Tuple[str, ...], date: pd.Timestamp):
        """Обучающие примеры состоят из признаков на основе данных для тикеров до указанной даты.

        :param tickers:
            Тикеры, для которых нужно составить обучающие примеры.
        :param date:
            Последняя дата, до которой можно использовать данные.
        """
        self._tickers = tickers
        self._date = date
        self._features = [cls(tickers, date) for cls in self.FEATURES]

    def get_features_names(self):
        """Название признаков."""
        return [feat.name for feat in self._features[1:]]

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

        Проверка осуществляется меток, СКО и только для используемых признаков.
        """
        it = iter(zip(self._features, params))
        label, (_, value) = next(it)
        label.check_bounds(**value)
        std, (_, value) = next(it)
        std.check_bounds(**value)
        for feat, (on_off, value) in it:
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

    @staticmethod
    def mean_std_days(params):
        """Количество дней, которое использовалось для расчета СКО для нормировки."""
        return params[0][1]["days"], params[1][1]["days"]

    def learn_pool_params(self, params):
        """Данные для создание catboost.Pool с обучающими примерами."""
        label = self._features[0]
        days = params[0][1]["days"]
        index = label.index
        try:
            loc = index.get_loc(self._date)
        except KeyError:
            raise POptimizerError(
                f"Для даты {self._date.date()} отсутствуют исторические котировки"
            )
        last_learn = loc - days
        index = index[last_learn::-days]
        data = [self.get(date, params) for date in index]
        df = pd.concat(data, axis=0, ignore_index=True)
        df.dropna(axis=0, inplace=True)
        return dict(
            data=df.iloc[:, 1:],
            label=df.iloc[:, 0],
            cat_features=self.categorical_features(),
            feature_names=list(df.columns[1:]),
        )

    def predict_pool_params(self, params):
        """Данные для создание catboost.Pool с примерами для прогноза."""
        df = self.get(self._date, params)
        return dict(
            data=df.iloc[:, 1:],
            label=None,
            cat_features=self.categorical_features(),
            feature_names=list(df.columns[1:]),
        )
