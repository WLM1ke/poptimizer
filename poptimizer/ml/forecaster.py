"""Составляет ML-прогноз."""
from typing import Tuple

import catboost
import numpy as np
import pandas as pd

from poptimizer import data, POptimizerError
from poptimizer.ml import examples, ledoit_wolf, cv
from poptimizer.ml.feature import YEAR_IN_TRADING_DAYS
from poptimizer.portfolio.metrics import Forecast

# Параметры данных и модели
PARAMS = (
    (
        (True, {"days": 21}),
        (True, {"days": 252}),
        (True, {}),
        (True, {"days": 252}),
        (True, {"days": 252}),
    ),
    {
        "bagging_temperature": 1,
        "depth": 6,
        "ignored_features": (),
        "l2_leaf_reg": 3,
        "learning_rate": 0.1,
        "one_hot_max_size": 2,
        "random_strength": 1,
    },
)


def cv_results(cases: examples.Examples):
    """Получает необходимые результаты кросс-валидации."""
    result = cv.cv_model(PARAMS, cases)
    return result["std"], result["r2"], result["params"]


def fit_clf(cv_params: tuple, cases: examples.Examples):
    """Тренирует ML-модель на основе параметров с учетом количества итераций."""
    data_params, model_params = cv_params
    learn_pool_params = cases.learn_pool_params(data_params)
    learn_pool = catboost.Pool(**learn_pool_params)
    clf = catboost.CatBoostRegressor(**model_params)
    clf.fit(learn_pool)
    return clf


def predict_mean(clf, cases: examples.Examples, cv_params, tickers):
    """Прогноз ожидаемой доходности."""
    predict_pool_params = cases.predict_pool_params(cv_params[0])
    predict_pool = catboost.Pool(**predict_pool_params)
    raw_prediction = pd.Series(clf.predict(predict_pool), list(tickers))
    scaler = predict_pool_params["data"].iloc[:, 0]
    return raw_prediction * scaler


def validate_cov(cov, cases: examples.Examples, cv_params):
    """Проверяет совпадение ковариации с использовавшейся для нормирования."""
    predict_pool_params = cases.predict_pool_params(cv_params[0])
    scaler = predict_pool_params["data"].iloc[:, 0]
    if not np.allclose(np.diag(cov), scaler.values ** 2):
        raise POptimizerError(
            "Расчетная ковариация не совпадает с использовавшейся для нормирования"
        )


def ledoit_wolf_cov(cases: examples.Examples, cv_params, tickers, date, ml_std):
    """Ковариационная матрица на основе Ledoit Wolf и вспомогательные данные.

    Оригинальная матрица корректируется в сторону не смещенной оценки на малой выборке и точность
    ML-прогноза.
    """
    mean_days, scaler_days = cases.mean_std_days(cv_params[0])
    returns = data.log_total_returns(tickers, date)
    returns = returns.iloc[-scaler_days:, ]
    cov, average_cor, shrinkage = ledoit_wolf.shrinkage(returns.values)
    cov *= YEAR_IN_TRADING_DAYS * scaler_days / (scaler_days - 1)
    validate_cov(cov, cases, cv_params)
    cov *= ml_std ** 2 * mean_days / YEAR_IN_TRADING_DAYS
    return cov, average_cor, shrinkage


def make_forecast(tickers: Tuple[str, ...], date: pd.Timestamp) -> Forecast:
    """Создает прогноз для набора тикеров на указанную дату.

    :param tickers:
        Тикеры, для которых необходимо составить прогноз.
    :param date:
        Дата, на которую нужен прогноз.
    :return:
        Прогнозная доходность, ковариация и дополнительная информация.
    """
    cases = examples.Examples(tickers, date)
    ml_std, r2, cv_params = cv_results(cases)
    clf = fit_clf(cv_params, cases)
    feature_importance = pd.Series(clf.feature_importances_, cases.get_features_names())
    mean = predict_mean(clf, cases, cv_params, tickers)
    cov, average_cor, shrinkage = ledoit_wolf_cov(
        cases, cv_params, tickers, date, ml_std
    )
    return Forecast(
        date=date,
        tickers=tickers,
        mean=mean,
        cov=cov,
        feature_importance=feature_importance,
        r2=r2,
        average_cor=average_cor,
        shrinkage=shrinkage,
    )
