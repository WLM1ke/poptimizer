import copy

import catboost
import numpy as np
import pandas as pd
import pytest

from poptimizer.config import POptimizerError
from poptimizer.ml import forecaster, examples, cv
from poptimizer.portfolio.metrics import Forecast

PARAMS = {
    "data": (
        ("Label", {"days": 20, "div_share": 0.0}),
        ("Scaler", {"days": 150}),
        ("Ticker", {}),
        ("Mom12m", {"days": 252, "periods": 1}),
        ("DivYield", {"days": 252, "periods": 1}),
        ("Mom1m", {"days": 21}),
    ),
    "model": {
        "bagging_temperature": 1,
        "depth": 6,
        "ignored_features": (),
        "l2_leaf_reg": 3,
        "learning_rate": 0.1,
        "one_hot_max_size": 2,
        "random_strength": 1,
    },
}

FORECAST = Forecast(
    pd.Timestamp("2019-03-16"),
    ("RTKM", "UPRO", "DSKY"),
    np.zeros((1,)),
    np.zeros((1,)),
    0,
    0,
    0,
    pd.Series(),
    0.0,
    0.0,
    0.0,
    0.0,
    0.0,
    PARAMS,
)


@pytest.fixture(name="cases")
def make_cases(monkeypatch):
    return examples.Examples(
        ("SNGSP", "VSMO", "DSKY"), pd.Timestamp("2018-12-14"), PARAMS["data"]
    )


@pytest.fixture(name="valid_result")
def make_valid_result(cases):
    return cv.valid_model(PARAMS, cases)


@pytest.fixture(name="train_predict_params")
def make_train_predict_params(cases):
    return cases.train_predict_pool_params()


def test_predict_mean(valid_result, train_predict_params):
    train_params, predict_params = train_predict_params
    learn_pool = catboost.Pool(**train_params)
    clf = catboost.CatBoostRegressor(**valid_result["model"])
    clf.fit(learn_pool)

    mean = forecaster.predict_mean(clf, predict_params)

    assert isinstance(mean, np.ndarray)
    assert len(mean) == 3
    assert mean[0] == pytest.approx(0.0006663620019700771)
    assert mean[1] == pytest.approx(0.000690691096292498)
    assert mean[2] == pytest.approx(0.0006907437838453376)


def test_validate_cov_error():
    predict_pool_params = dict()
    predict_pool_params["data"] = pd.DataFrame([[1, 0], [2, 0], [3, 0]])
    cov = np.array([[1, 0, 0], [0, 4, 0], [0, 0, 9.1]])
    with pytest.raises(POptimizerError) as error:
        forecaster.validate_cov(cov, predict_pool_params)
    assert (
        "Расчетная ковариация не совпадает с использовавшейся для нормирования"
        in str(error.value)
    )


def test_validate_cache():
    assert forecaster.validate_cache(
        FORECAST, ("RTKM", "UPRO", "DSKY"), pd.Timestamp("2019-03-16"), PARAMS
    )


def test_non_validate_cache():
    assert not forecaster.validate_cache(
        FORECAST, ("RTKM", "UPRO", "DSKY", "FEES"), pd.Timestamp("2019-03-16"), PARAMS
    )
    assert not forecaster.validate_cache(
        FORECAST, ("RTKM", "UPRO", "DSKY"), pd.Timestamp("2019-03-15"), PARAMS
    )
    new_params = copy.deepcopy(PARAMS)
    new_params["model"]["learning_rate"] = 0.11
    assert not forecaster.validate_cache(
        FORECAST, ("RTKM", "UPRO", "DSKY"), pd.Timestamp("2019-03-16"), new_params
    )


def test_ledoit_wolf_cov(valid_result, train_predict_params):
    _, predict_params = train_predict_params
    cov, average_cor, shrinkage = forecaster.ledoit_wolf_cov(
        ("DSKY", "SNGSP", "VSMO"),
        pd.Timestamp("2018-12-14"),
        predict_params,
        valid_result,
    )
    assert isinstance(cov, np.ndarray)
    assert cov[0, 0] == pytest.approx(3.756411365098592e-05)
    assert cov[2, 1] == pytest.approx(4.640198385583775e-06)
    assert average_cor == pytest.approx(0.10588718234140086)
    assert shrinkage == pytest.approx(1.0)


def test_get_forecast():
    forecast = forecaster.get_forecast(
        ("DSKY", "SNGSP", "VSMO"), pd.Timestamp("2018-12-14"), PARAMS
    )
    assert isinstance(forecast, Forecast)
    assert forecast.date == pd.Timestamp("2018-12-14")
    assert forecast.tickers == ("DSKY", "SNGSP", "VSMO")
    assert isinstance(forecast.mean, np.ndarray)
    assert forecast.mean[1] == pytest.approx(0.1740541562657095)
    assert isinstance(forecast.cov, np.ndarray)
    assert forecast.cov[2, 1] == pytest.approx(0.0011693299931671113)
    assert isinstance(forecast.feature_importance, pd.Series)
    assert np.allclose(
        forecast.feature_importance, [27.084442, 11.017218, 7.570018, 54.328323, 0]
    )
    assert forecast.r2 == pytest.approx(-0.002544220995196911)
    assert forecast.ev == pytest.approx(0.023249213701098337)
    assert forecast.r == pytest.approx(0.17736926019064034)
    assert forecast.average_cor == pytest.approx(0.10588718234140086)
    assert forecast.shrinkage == pytest.approx(1)
