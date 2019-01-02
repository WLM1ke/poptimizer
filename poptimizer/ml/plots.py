"""Различные графики для анализа ML-модели."""
import copy
from typing import Tuple

import catboost
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn import model_selection

from poptimizer import config
from poptimizer.ml import examples, forecaster, cv
from poptimizer.ml.feature import YEAR_IN_TRADING_DAYS

# Размер графиков
PLOTS_SIZE = 8

# Доли общего числа данных для построения кривой обучения
FRACTIONS = np.linspace(0.1, 1.0, 10)

# Параметры кривых частичной зависимости
QUANTILE = np.linspace(0.05, 0.95, 19)


def learning_curve(tickers: Tuple[str, ...], date: pd.Timestamp):
    """Рисует кривую обучения ML-модель.

    :param tickers:
        Тикеры, для которых необходимо составить ML-модель.
    :param date:
        Дата, на которую составляется ML-модель.
    """
    params = config.ML_PARAMS
    cases = examples.Examples(tickers, date)
    _, _, cv_params = forecaster.cv_results(cases, params)
    data_params, model_params = cv_params
    learn_pool_params = cases.learn_pool_params(data_params)
    model_params["cat_features"] = cases.categorical_features()
    train_sizes, train_scores, test_scores = model_selection.learning_curve(
        catboost.CatBoostRegressor(**model_params),
        learn_pool_params["data"],
        learn_pool_params["label"],
        train_sizes=list(FRACTIONS),
        cv=cv.FOLDS_COUNT,
        scoring="neg_mean_squared_error",
        shuffle=True,
        random_state=cv.SEED,
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
    cases = examples.Examples(tickers, date)
    _, _, cv_params = forecaster.cv_results(cases, params)
    clf, _ = forecaster.fit_clf(cv_params, cases)
    pool_params = cases.predict_pool_params(cv_params[0])
    pool_params["label"] = None
    n_plots = len(cases.FEATURES) - 1 - len(cases.categorical_features())
    figsize = (PLOTS_SIZE * n_plots, PLOTS_SIZE)
    fig, ax_list = plt.subplots(1, n_plots, figsize=figsize, sharey=True)
    fig.tight_layout(pad=3, h_pad=5)
    axs = iter(ax_list)
    for n, feature in enumerate(cases.FEATURES[1:]):
        if feature.is_categorical():
            continue
        ax = next(axs)
        predict_pool_params = copy.deepcopy(pool_params)
        quantiles = predict_pool_params["data"].iloc[:, n].quantile(QUANTILE).values
        x = []
        y = []
        for quantile in quantiles:
            x.append(quantile)
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
        ax.plot(x, y)
    plt.show()


def draw_cross_val_predict(tickers: Tuple[str, ...], date: pd.Timestamp):
    """График прогнозируемого с помощью кросс-валидации значения против фактического значения."""
    params = config.ML_PARAMS
    cases = examples.Examples(tickers, date)
    _, _, cv_params = forecaster.cv_results(cases, params)
    data_params, model_params = cv_params
    learn_pool_params = cases.learn_pool_params(data_params)
    model_params["cat_features"] = cases.categorical_features()

    predicted = model_selection.cross_val_predict(
        catboost.CatBoostRegressor(**model_params),
        learn_pool_params["data"],
        learn_pool_params["label"],
        cv=cv.FOLDS_COUNT,
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


if __name__ == "__main__":
    POSITIONS = dict(
        AKRN=563,
        BANE=236 + 45,
        BANEP=1644 + 320,
        CBOM=25400,
        CHMF=1770,
        DSKY=0 + 2090,
        FEES=6_270_000,
        GMKN=45,
        KZOS=5100 + 3400,
        LKOH=270,
        LSNGP=6600,
        LSRG=1700 + 0 + 80,
        MAGN=3500 + 1300,
        MOEX=4190,
        MSRS=128_000 + 117_000,
        MSTT=820,
        MTSS=4960,
        NKNCP=8900,
        NLMK=3180 + 4570,
        NMTP=11000 + 11000,
        PHOR=0 + 28,
        PIKK=1740 + 10 + 90,
        PMSBP=28730 + 4180 + 3360,
        PRTK=8000 + 3600,
        RASP=3070 + 0 + 630,
        RTKM=1080 + 30,
        RTKMP=65000 + 0 + 1700,
        SIBN=0 + 710,
        SNGSP=53200 + 0 + 9800,
        TATN=150 + 420,
        TATNP=3420 + 290 + 100,
        TTLK=1_980_000,
        UPRO=901_000 + 0 + 9000,
        VSMO=161 + 3,
        # Бумаги с нулевым весом
        ENRU=0,
        MTLRP=0,
        ROSN=0,
        NVTK=0,
        AFLT=0,
        ALRS=0,
        MRKV=0,
        MRKP=0,
        KBTK=0,
        NKHP=0,
        MRKU=0,
        DVEC=0,
        VTBR=0,
    )
    DATE = "2018-12-29"
    draw_cross_val_predict(tuple(sorted(POSITIONS)), pd.Timestamp(DATE))
