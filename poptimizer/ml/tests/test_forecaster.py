import numpy as np
import pandas as pd
import pytest

from poptimizer.config import POptimizerError
from poptimizer.ml import forecaster, examples_old, feature_old
from poptimizer.portfolio.metrics import Forecast

PARAMS = (
    (
        (True, {"days": 20}),
        (True, {"days": 150}),
        (True, {}),
        (True, {"days": 252}),
        (True, {"days": 252}),
        (False, {"days": 21}),
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

FEATURES = [
    feature_old.Label,
    feature_old.STD,
    feature_old.Ticker,
    feature_old.Mom12m,
    feature_old.DivYield,
    feature_old.Mom1m,
]


# noinspection PyUnresolvedReferences
@pytest.fixture(name="cases")
def make_cases(monkeypatch):
    monkeypatch.setattr(examples_old.Examples, "FEATURES", FEATURES)
    return examples_old.Examples(("SNGSP", "VSMO", "DSKY"), pd.Timestamp("2018-12-14"))


@pytest.fixture(name="cv_results")
def make_cv_results(cases):
    return forecaster.cv_results(cases, PARAMS)


@pytest.fixture(name="clf_n_cases")
def make_fit_clf(cases, cv_results):
    _, _, cv_params = cv_results
    return forecaster.fit_clf(cv_params, cases)


def test_cv_results(cv_results):
    ml_std, r2, cv_params = cv_results
    assert ml_std == pytest.approx(0.18377877393031805)
    assert r2 == pytest.approx(0.08242085969748303)
    assert "iterations" in cv_params[1]


def test_fit_clf(clf_n_cases):
    clf, n_cases = clf_n_cases
    assert clf.is_fitted()
    assert n_cases == 208


def test_predict_mean(cases, cv_results, clf_n_cases):
    clf, _ = clf_n_cases
    _, _, cv_params = cv_results
    mean = forecaster.predict_mean(clf, cases, cv_params)

    assert isinstance(mean, np.ndarray)
    assert len(mean) == 3
    assert mean[0] == pytest.approx(0.0004924419093643773)
    assert mean[1] == pytest.approx(0.00027158276622838416)
    assert mean[2] == pytest.approx(0.00022278753502165055)


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
    assert cov[2, 1] == pytest.approx(0.0005221095750566297)
    assert average_cor == pytest.approx(0.10588718234140086)
    assert shrinkage == pytest.approx(1.0)


# noinspection PyUnresolvedReferences
def test_make_forecast(monkeypatch):
    monkeypatch.setattr(examples_old.Examples, "FEATURES", FEATURES)
    forecast = forecaster.make_forecast(
        ("SNGSP", "VSMO", "DSKY"), pd.Timestamp("2018-12-14"), PARAMS
    )
    assert isinstance(forecast, Forecast)
    assert forecast.date == pd.Timestamp("2018-12-14")
    assert forecast.tickers == ("SNGSP", "VSMO", "DSKY")
    assert isinstance(forecast.mean, np.ndarray)
    assert forecast.mean[1] == pytest.approx(0.0684388570895528)
    assert isinstance(forecast.cov, np.ndarray)
    assert forecast.cov[2, 1] == pytest.approx(0.0011109458910028857)
    assert isinstance(forecast.feature_importance, pd.Series)
    assert np.allclose(
        forecast.feature_importance, [25.749377, 12.777575, 28.876857, 32.596191, 0]
    )
    assert forecast.r2 == pytest.approx(0.08242085969748303)
    assert forecast.average_cor == pytest.approx(0.10588718234140086)
    assert forecast.shrinkage == pytest.approx(1)
