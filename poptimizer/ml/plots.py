"""Различные графики для анализа ML-модели."""
import copy
from typing import Tuple, Iterator

import catboost
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from poptimizer import config
from poptimizer.config import YEAR_IN_TRADING_DAYS
from poptimizer.ml import examples, cv

__all__ = ["partial_dependence_curve"]

# Размер графиков
PLOTS_SIZE = 5

# Параметры кривых частичной зависимости
QUANTILE = np.linspace(0.01, 0.99, 99)


def train_clf(
    cases: examples.Examples, params: dict
) -> Tuple[catboost.CatBoostRegressor, dict]:
    """Тренирует модель, возвращает ее и примеры для обучения."""
    valid_params = cv.valid_model(params, cases)
    model_params = valid_params["model"]
    clf = catboost.CatBoostRegressor(**model_params)
    train_pool_params, _ = cases.train_predict_pool_params()
    train_pool = catboost.Pool(**train_pool_params)
    clf.fit(train_pool)
    train_pool_params["label"] = None
    return clf, train_pool_params


def axs_iter(n_plots: int) -> Iterator:
    """Создает прямоугольный набор из графиков вытянутый по горизонтали близкий к квадрату.

    Возвращает итератор осей.
    """
    row_n = int(n_plots ** 0.5)
    col_n = (n_plots + row_n - 1) // row_n
    fig_size = (PLOTS_SIZE * col_n, PLOTS_SIZE * row_n)
    fig, ax_list = plt.subplots(
        row_n, col_n, figsize=fig_size, sharey="all", num="Partial dependence curves"
    )
    fig.tight_layout(pad=3, h_pad=5)
    return iter(ax_list.flatten())


def partial_dependence_curve(tickers: Tuple[str, ...], date: pd.Timestamp) -> list:
    """Рисует кривые частичной зависимости для численных параметров.

    :param tickers:
        Тикеры, для которых необходимо составить ML-модель.
    :param date:
        Дата, на которую составляется ML-модель.
    """
    params = config.ML_PARAMS
    cases = examples.Examples(tickers, date, params["data"])
    clf, train_pool_params = train_clf(cases, params)
    n_plots = len(train_pool_params["data"].columns) - len(cases.categorical_features())
    axs = axs_iter(n_plots)
    results = []
    for n, name in enumerate(train_pool_params["data"]):
        if n in cases.categorical_features():
            continue
        ax = next(axs)
        pool_params = copy.deepcopy(train_pool_params)
        quantiles = pool_params["data"].iloc[:, n].quantile(QUANTILE).values
        y = []
        for quantile in quantiles:
            pool_params["data"].iloc[:, n] = quantile
            predict_pool = catboost.Pool(**pool_params)
            raw_prediction = clf.predict(predict_pool)
            prediction = raw_prediction * YEAR_IN_TRADING_DAYS
            y.append(prediction.mean())
        ax.set_title(f"{name}")
        ax.tick_params(labelleft=True)
        ax.plot(quantiles, y)
        results.append((quantiles, y))
    plt.show()
    return results
