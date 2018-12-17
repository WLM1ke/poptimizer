import numpy as np
import pandas as pd
import pytest

from poptimizer import POptimizerError
from poptimizer.ml import forecaster, examples
from poptimizer.ml.feature import YEAR_IN_TRADING_DAYS
from poptimizer.portfolio.metrics import Forecast

PARAMS = (
    (
        (True, {"days": 20}),
        (True, {"days": 150}),
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


@pytest.fixture(scope="module", name="cases")
def make_cases():
    return examples.Examples(("SNGSP", "VSMO", "DSKY"), pd.Timestamp("2018-12-14"))


@pytest.fixture(scope="module", name="cv_results")
def make_cv_results(cases):
    return forecaster.cv_results(cases, PARAMS)


@pytest.fixture(scope="module", name="clf")
def make_fit_clf(cases, cv_results):
    _, _, cv_params = cv_results
    return forecaster.fit_clf(cv_params, cases)


def test_cv_results(cv_results):
    ml_std, r2, cv_params = cv_results
    assert ml_std == pytest.approx(3.2689512418161755 / YEAR_IN_TRADING_DAYS ** 0.5)
    assert r2 == pytest.approx(0.17408768222445936)
    assert "iterations" in cv_params[1]


def test_fit_clf(clf):
    assert clf.is_fitted()


def test_predict_mean(cases, cv_results, clf):
    _, _, cv_params = cv_results
    mean = forecaster.predict_mean(clf, cases, cv_params)

    assert isinstance(mean, np.ndarray)
    assert len(mean) == 3
    assert mean[0] == pytest.approx(0.06149871693585873 / YEAR_IN_TRADING_DAYS)
    assert mean[1] == pytest.approx(-0.009076847544294444 / YEAR_IN_TRADING_DAYS)
    assert mean[2] == pytest.approx(-0.03566373524243131 / YEAR_IN_TRADING_DAYS)


def test_validate_cov(cases, cv_results):
    _, _, cv_params = cv_results
    cov = np.array([[1, 0, 0], [0, 1, 0], [0, 0, 1]])
    with pytest.raises(POptimizerError) as error:
        forecaster.validate_cov(cov, cases, cv_params)
    assert (
        "Расчетная ковариация не совпадает с использовавшейся для нормирования"
        == str(error.value)
    )


def test_ledoit_wolf_cov(cases, cv_results):
    _, _, cv_params = cv_results
    cov, average_cor, shrinkage = forecaster.ledoit_wolf_cov(
        cases, cv_params, ("SNGSP", "VSMO", "DSKY"), pd.Timestamp("2018-12-14"), 2
    )
    assert isinstance(cov, np.ndarray)
    assert cov[0, 0] == pytest.approx(0.015626193162078562)
    assert cov[2, 1] == pytest.approx(0.0004585881710322543)
    assert average_cor == pytest.approx(0.08777292794188181)
    assert shrinkage == pytest.approx(1.0)


def test_make_forecast():
    forecast = forecaster.make_forecast(
        ("SNGSP", "VSMO", "DSKY"), pd.Timestamp("2018-12-14"), PARAMS
    )
    assert isinstance(forecast, Forecast)
    assert forecast.date == pd.Timestamp("2018-12-14")
    assert forecast.tickers == ("SNGSP", "VSMO", "DSKY")
    assert isinstance(forecast.mean, np.ndarray)
    assert forecast.mean[1] == pytest.approx(-0.009076847544294444)
    assert isinstance(forecast.cov, np.ndarray)
    assert forecast.cov[2, 1] == pytest.approx(0.0012251231394680528)
    assert isinstance(forecast.feature_importance, pd.Series)
    assert np.allclose(
        forecast.feature_importance, [35.60526857, 9.65125932, 24.77469142, 29.96878069]
    )
    assert forecast.r2 == pytest.approx(0.17408768222445936)
    assert forecast.average_cor == pytest.approx(0.08777292794188181)
    assert forecast.shrinkage == pytest.approx(1)
