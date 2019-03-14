"""Составляет ML-прогноз."""
from typing import Tuple

import catboost
import numpy as np
import pandas as pd

from poptimizer import data
from poptimizer.config import POptimizerError, ML_PARAMS
from poptimizer.ml import examples, ledoit_wolf, cv
from poptimizer.ml.feature import YEAR_IN_TRADING_DAYS
from poptimizer.portfolio import Forecast


def predict_mean(clf, predict_pool_params):
    """Прогноз ожидаемой доходности."""
    predict_pool = catboost.Pool(**predict_pool_params)
    raw_prediction = clf.predict(predict_pool)
    scaler = predict_pool_params["data"].iloc[:, 0]
    return raw_prediction * scaler.values


def validate_cov(cov, predict_pool_params):
    """Проверяет совпадение ковариации с использовавшейся для нормирования."""
    scaler = predict_pool_params["data"].iloc[:, 0]
    if not np.allclose(np.diag(cov), scaler.values ** 2):
        raise POptimizerError(
            "Расчетная ковариация не совпадает с использовавшейся для нормирования"
        )


def ledoit_wolf_cov(predict_pool_params, valid_result, tickers, date):
    """Ковариационная матрица на основе Ledoit Wolf и вспомогательные данные.

    Оригинальная матрица корректируется в сторону не смещенной оценки на малой выборке и точность
    ML-прогноза.
    """
    mean_days, scaler_days = (
        valid_result["data"][0][1]["days"],
        valid_result["data"][1][1]["days"],
    )
    returns = data.log_total_returns(tickers, date)
    returns = returns.iloc[-scaler_days:,]
    cov, average_cor, shrinkage = ledoit_wolf.shrinkage(returns.values)
    cov *= scaler_days / (scaler_days - 1)
    validate_cov(cov, predict_pool_params)
    cov *= valid_result["std"] ** 2 * mean_days
    return cov, average_cor, shrinkage


def make_forecast(
    tickers: Tuple[str, ...], date: pd.Timestamp, params=ML_PARAMS
) -> Forecast:
    """Создает прогноз для набора тикеров на указанную дату.

    :param tickers:
        Тикеры, для которых необходимо составить прогноз.
    :param date:
        Дата, на которую нужен прогноз.
    :param params:
        Параметры ML-модели для прогноза.
    :return:
        Прогнозная доходность, ковариация и дополнительная информация.
    """
    cases = examples.Examples(tickers, date, params["data"])

    valid_result = cv.valid_model(params, cases)

    train_params, predict_params = cases.train_predict_pool_params()
    learn_pool = catboost.Pool(**train_params)
    clf = catboost.CatBoostRegressor(**valid_result["model"])
    clf.fit(learn_pool)
    num_cases = len(train_params)

    feature_importance = pd.Series(
        clf.feature_importances_, cases.get_features_names(), name="Importance"
    )
    mean = predict_mean(clf, predict_params)
    cov, average_cor, shrinkage = ledoit_wolf_cov(
        predict_params, valid_result, tickers, date
    )
    return Forecast(
        date=date,
        tickers=tickers,
        mean=mean * YEAR_IN_TRADING_DAYS,
        cov=cov * YEAR_IN_TRADING_DAYS,
        num_cases=num_cases,
        trees=valid_result["model"]["iterations"],
        depth=valid_result["model"]["depth"],
        feature_importance=feature_importance,
        r2=valid_result["r2"],
        average_cor=average_cor,
        shrinkage=shrinkage,
    )
