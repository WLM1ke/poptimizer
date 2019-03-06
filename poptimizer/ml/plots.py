"""Различные графики для анализа ML-модели."""
import copy
from typing import Tuple

import catboost
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn import model_selection

from poptimizer import config
from poptimizer.ml import examples_old, forecaster_old, cv_old
from poptimizer.ml.feature import YEAR_IN_TRADING_DAYS

__all__ = ["learning_curve", "partial_dependence_curve", "cross_val_predict_plot"]

# Размер графиков
PLOTS_SIZE = 8

# Доли общего числа данных для построения кривой обучения
FRACTIONS = np.linspace(0.1, 1.0, 10)

# Параметры кривых частичной зависимости
QUANTILE = np.linspace(0.01, 0.99, 99)


def learning_curve(tickers: Tuple[str, ...], date: pd.Timestamp):
    """Рисует кривую обучения ML-модель.

    :param tickers:
        Тикеры, для которых необходимо составить ML-модель.
    :param date:
        Дата, на которую составляется ML-модель.
    """
    params = config.ML_PARAMS
    cases = examples_old.Examples(tickers, date)
    _, _, cv_params = forecaster_old.cv_results(cases, params)
    data_params, model_params = cv_params
    learn_pool_params = cases.learn_pool_params(data_params)
    model_params["cat_features"] = cases.categorical_features()
    train_sizes, train_scores, test_scores = model_selection.learning_curve(
        catboost.CatBoostRegressor(**model_params),
        learn_pool_params["data"],
        learn_pool_params["label"],
        train_sizes=list(FRACTIONS),
        cv=model_selection.KFold(
            cv_old.FOLDS_COUNT, shuffle=True, random_state=cv_old.SEED
        ),
        scoring="neg_mean_squared_error",
        shuffle=True,
        random_state=cv_old.SEED,
    )
    fig, ax = plt.subplots(figsize=(PLOTS_SIZE, PLOTS_SIZE))
    fig.tight_layout(pad=3, h_pad=5)
    ax.set_title(f"Learning curve")
    ax.set_xlabel("Training examples")
    mean_days, _ = cases.mean_std_days(cv_params[0])
    train_scores_mean = (-np.mean(train_scores, axis=1) * mean_days) ** 0.5
    test_scores_mean = (-np.mean(test_scores, axis=1) * mean_days) ** 0.5
    ax.grid()
    ax.plot(train_sizes, train_scores_mean, "o-", color="r", label="Training score")
    ax.plot(
        train_sizes, test_scores_mean, "o-", color="g", label="Cross-validation score"
    )
    ax.legend(loc="best")
    plt.show()
    return train_sizes, train_scores_mean, test_scores_mean


def partial_dependence_curve(tickers: Tuple[str, ...], date: pd.Timestamp):
    """Рисует кривые частичной зависимости для численных параметров.

    :param tickers:
        Тикеры, для которых необходимо составить ML-модель.
    :param date:
        Дата, на которую составляется ML-модель.
    """
    params = config.ML_PARAMS
    cases = examples_old.Examples(tickers, date)
    _, _, cv_params = forecaster_old.cv_results(cases, params)
    clf, _ = forecaster_old.fit_clf(cv_params, cases)
    pool_params = cases.predict_pool_params(cv_params[0])
    pool_params["label"] = None
    n_plots = len(cases.FEATURES) - 1 - len(cases.categorical_features())
    fig_size = (PLOTS_SIZE * n_plots, PLOTS_SIZE)
    fig, ax_list = plt.subplots(1, n_plots, figsize=fig_size, sharey="all")
    fig.tight_layout(pad=3, h_pad=5)
    axs = iter(ax_list)
    results = []
    for n, feature in enumerate(cases.FEATURES[1:]):
        if feature.is_categorical():
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
        ax.set_title(f"{feature.__name__}")
        ax.tick_params(labelleft=True)
        ax.plot(quantiles, y)
        results.append((quantiles, y))
    plt.show()
    return results


def cross_val_predict_plot(tickers: Tuple[str, ...], date: pd.Timestamp):
    """График прогнозируемого с помощью кросс-валидации значения против фактического значения."""
    params = config.ML_PARAMS
    cases = examples_old.Examples(tickers, date)
    _, _, cv_params = forecaster_old.cv_results(cases, params)
    data_params, model_params = cv_params
    learn_pool_params = cases.learn_pool_params(data_params)
    model_params["cat_features"] = cases.categorical_features()
    predicted = model_selection.cross_val_predict(
        catboost.CatBoostRegressor(**model_params),
        learn_pool_params["data"],
        learn_pool_params["label"],
        cv=cv_old.FOLDS_COUNT,
    )
    x = (
        learn_pool_params["label"]
        * learn_pool_params["data"].iloc[:, 0]
        * YEAR_IN_TRADING_DAYS
    )
    y = predicted * learn_pool_params["data"].iloc[:, 0] * YEAR_IN_TRADING_DAYS
    fig, ax = plt.subplots(figsize=(PLOTS_SIZE, PLOTS_SIZE))
    fig.tight_layout(pad=3, h_pad=5)
    ax.scatter(x, y, edgecolors=(0, 0, 0))
    ax.set_xlim(np.percentile(x, 5), np.percentile(x, 95))
    ax.set_ylim(np.percentile(x, 5), np.percentile(x, 95))
    ax.plot(
        [np.percentile(x, 5), np.percentile(x, 95)],
        [np.percentile(x, 5), np.percentile(x, 95)],
        "k--",
        lw=1,
    )
    ax.set_xlabel("Measured")
    ax.set_ylabel("Cross-Validated Prediction")
    plt.show()
    return x, y
