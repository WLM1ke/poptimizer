"""Составляет ML-прогноз."""
from typing import Tuple

import catboost
import numpy as np
import pandas as pd

from poptimizer import data, config, store
from poptimizer.ml import examples, ledoit_wolf, cv
from poptimizer.ml.feature import YEAR_IN_TRADING_DAYS
from poptimizer.portfolio import Forecast

# Ключ для хранений кеша прогноза
FORECAST = "forecast"


def predict_mean(
    clf: catboost.CatBoostRegressor, predict_pool_params: dict
) -> np.array:
    """Прогноз ожидаемой доходности."""
    predict_pool = catboost.Pool(**predict_pool_params)
    return clf.predict(predict_pool)


def validate_cov(cov: np.array, predict_pool_params: dict):
    """Проверяет совпадение ковариации с использовавшейся для нормирования."""
    scaler = predict_pool_params["data"].iloc[:, 0]
    if not np.allclose(np.diag(cov), scaler.values ** 2):
        raise config.POptimizerError(
            f"Расчетная ковариация не совпадает с использовавшейся для нормирования:"
            f"\n{np.diag(cov)}"
            f"\n{scaler.values ** 2}"
        )


def ledoit_wolf_cov(
    tickers: tuple, date: pd.Timestamp, predict_pool_params: dict, valid_result: dict
) -> Tuple[np.array, float, float]:
    """Ковариационная матрица на основе Ledoit Wolf и вспомогательные данные.

    Оригинальная матрица корректируется в сторону не смещенной оценки на малой выборке и точность
    ML-прогноза.
    """
    mean_days = valid_result["data"][0][1]["days"]
    scaler_days = valid_result["data"][1][1]["days"]
    returns = data.log_total_returns(tickers, date)
    returns = returns.iloc[-scaler_days:,]
    cov, average_cor, shrinkage = ledoit_wolf.shrinkage(returns.values)
    cov *= scaler_days / (scaler_days - 1)
    validate_cov(cov, predict_pool_params)
    # Ковариация увеличивается пропорционально отношению квадрата ошибки к СКО. Так как ковариация
    # считалась для среднего за mean_days увеличивается для получения дневной ковариации.
    cov *= valid_result["std"] ** 2 * mean_days
    return cov, average_cor, shrinkage


def validate_cache(
    forecast_cache: Forecast, tickers: tuple, date: pd.Timestamp, params: dict
) -> bool:
    """Проверяет, что кэш создан для тех же параметров."""
    if (
        forecast_cache is not None
        and tickers == forecast_cache.tickers
        and date == forecast_cache.date
        and params == forecast_cache.params
    ):
        return True
    return False


def make_forecast(tickers: tuple, date: pd.Timestamp, params: dict) -> Forecast:
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
    num_cases = len(train_params["data"])
    feature_importance = pd.Series(
        clf.feature_importances_, cases.get_features_names(), name="Importance"
    )
    mean = predict_mean(clf, predict_params)
    cov, average_cor, shrinkage = ledoit_wolf_cov(
        tickers, date, predict_params, valid_result
    )
    forecast = Forecast(
        date=date,
        tickers=tickers,
        mean=mean * YEAR_IN_TRADING_DAYS,
        cov=cov * YEAR_IN_TRADING_DAYS,
        num_cases=num_cases,
        trees=valid_result["model"]["iterations"],
        depth=valid_result["model"]["depth"],
        feature_importance=feature_importance,
        r2=valid_result["r2"],
        ev=valid_result["ev"],
        r=valid_result["r"],
        average_cor=average_cor,
        shrinkage=shrinkage,
        params=params,
    )
    return forecast


def get_forecast(tickers: Tuple[str, ...], date: pd.Timestamp, params=None) -> Forecast:
    """Создает или загружает закешированный прогноз для набора тикеров на указанную дату.

    :param tickers:
        Тикеры, для которых необходимо составить прогноз.
    :param date:
        Дата, на которую нужен прогноз.
    :param params:
        Параметры ML-модели для прогноза.
    :return:
        Прогнозная доходность, ковариация и дополнительная информация.
    """
    mongodb = store.MongoDB()
    forecast_cache = mongodb[FORECAST]
    params = params or config.ML_PARAMS
    if validate_cache(forecast_cache, tickers, date, params):
        return forecast_cache
    forecast = make_forecast(tickers, date, params)
    mongodb[FORECAST] = forecast
    return forecast
