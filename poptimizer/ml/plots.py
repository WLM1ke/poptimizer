"""Различные графики для анализа ML-модели."""
import copy
from typing import Tuple

import catboost
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from poptimizer import config
from poptimizer.ml import examples, forecaster
from poptimizer.ml.feature import YEAR_IN_TRADING_DAYS

__all__ = ["partial_dependence_curve"]

# Размер графиков
PLOTS_SIZE = 6

# Параметры кривых частичной зависимости
QUANTILE = np.linspace(0.01, 0.99, 99)


def partial_dependence_curve(tickers: Tuple[str, ...], date: pd.Timestamp):
    """Рисует кривые частичной зависимости для численных параметров.

    :param tickers:
        Тикеры, для которых необходимо составить ML-модель.
    :param date:
        Дата, на которую составляется ML-модель.
    """
    params = config.ML_PARAMS
    cases = examples.Examples(tickers, date, params[0])
    _, _, cv_params = forecaster.cv_results(cases, params)
    clf, _, _ = forecaster.fit_clf(cv_params, cases)
    pool_params, _ = cases.train_predict_pool_params()
    pool_params["label"] = None
    n_plots = len(params[0]) - 1 - len(cases.categorical_features())
    row_n = int(n_plots ** 0.5)
    col_n = (n_plots + row_n - 1) // row_n
    fig_size = (PLOTS_SIZE * col_n, PLOTS_SIZE * row_n)
    fig, ax_list = plt.subplots(
        row_n, col_n, figsize=fig_size, sharey="all", num="Partial dependence curves"
    )
    ax_list = ax_list.flatten()
    fig.tight_layout(pad=3, h_pad=5)
    axs = iter(ax_list)
    results = []
    for n, (name, _) in enumerate(params[0][1:]):
        if n in cases.categorical_features():
            continue
        ax = next(axs)
        predict_pool_params = copy.deepcopy(pool_params)
        quantiles = predict_pool_params["data"].iloc[:, n].quantile(QUANTILE).values
        y = []
        for quantile in quantiles:
            predict_pool_params["data"].iloc[:, n] = quantile
            predict_pool = catboost.Pool(**predict_pool_params)
            raw_prediction = clf.predict(predict_pool)
            prediction = (
                raw_prediction
                * predict_pool_params["data"].iloc[:, 0]
                * YEAR_IN_TRADING_DAYS
            )
            y.append(prediction.values.mean())
        ax.set_title(f"{name}")
        ax.tick_params(labelleft=True)
        ax.plot(quantiles, y)
        results.append((quantiles, y))
    plt.show()
    return results
