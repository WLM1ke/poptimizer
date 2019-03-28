import numpy as np
import pandas as pd
import pytest

from poptimizer import config
from poptimizer.portfolio import Portfolio, portfolio, metrics
from poptimizer.portfolio.metrics import Metrics, Forecast
from poptimizer.portfolio.portfolio import CASH, PORTFOLIO

ML_PARAMS = {
    "data": (
        ("Label", {"days": 30}),
        ("STD", {"days": 252}),
        ("Ticker", {}),
        ("Mom12m", {"days": 252}),
        ("DivYield", {"days": 252, "periods": 1}),
        ("Mom1m", {"on_off": False, "days": 21}),
    ),
    "model": {
        "bagging_temperature": 1.16573715129796,
        "depth": 4,
        "l2_leaf_reg": 2.993522023941868,
        "learning_rate": 0.10024901894125209,
        "one_hot_max_size": 100,
        "random_strength": 0.9297802156425078,
        "ignored_features": [1],
    },
}


class SimpleMetrics(Metrics):
    def _forecast_func(self):
        mean = np.array([1.0, 2.0, 3.0])
        cov = np.array([[9.0, 3.0, 1.0], [3.0, 4.0, 0.5], [1.0, 0.5, 1.0]])
        port = self._portfolio
        return Forecast(
            port.date,
            tuple(port.index[:-2]),
            mean,
            cov,
            10,
            20,
            3,
            pd.Series(),
            0.0,
            0.0,
            0.0,
            ML_PARAMS,
        )


@pytest.fixture(scope="module", name="metrics_and_index")
def create_metrics_and_index():
    date = "2018-12-10"
    positions = dict(LSNGP=161, MSTT=505, PIKK=57)
    portfolio = Portfolio(date, 10000, positions)
    metrics = SimpleMetrics(portfolio, 3)
    index = pd.Index(["LSNGP", "MSTT", "PIKK", CASH, PORTFOLIO])
    return metrics, index


def test_mean(metrics_and_index):
    metrics, index = metrics_and_index
    mean = metrics.mean

    assert isinstance(mean, pd.Series)
    # noinspection PyUnresolvedReferences
    assert (mean.index == index).all()
    assert np.allclose(mean, [1, 2, 3, 0, 1.83287191547398])


def test_std(metrics_and_index):
    metrics, index = metrics_and_index
    std = metrics.std

    assert isinstance(std, pd.Series)
    # noinspection PyUnresolvedReferences
    assert (std.index == index).all()
    assert np.allclose(std, [3, 2, 1, 0, 1.4097985185379])


def test_beta(metrics_and_index):
    metrics, index = metrics_and_index
    beta = metrics.beta

    assert isinstance(beta, pd.Series)
    # noinspection PyUnresolvedReferences
    assert (beta.index == index).all()
    assert np.allclose(
        beta, [1.63223121498382, 1.31081912817928, 0.323000567807792, 0, 1]
    )


def test_lower_bound(metrics_and_index):
    metrics, index = metrics_and_index
    lower_bound = metrics.lower_bound

    assert isinstance(lower_bound, pd.Series)
    # noinspection PyUnresolvedReferences
    assert (lower_bound.index == index).all()
    assert np.allclose(
        lower_bound,
        [-2.0511171487955, -1.34799086497829, 0.294634278017675, 0, -0.951580539669401],
    )


def test_gradient(metrics_and_index):
    metrics, index = metrics_and_index
    gradient = metrics.gradient

    assert isinstance(gradient, pd.Series)
    # noinspection PyUnresolvedReferences
    assert (gradient.index == index).all()
    assert np.allclose(
        gradient,
        [-1.0995366091261, -0.396410325308889, 1.24621481768708, 0.951580539669401, 0],
    )


def test_str(metrics_and_index):
    metrics, _ = metrics_and_index
    assert "КЛЮЧЕВЫЕ МЕТРИКИ ПОРТФЕЛЯ" in str(metrics)


def test_std_gradient():
    pos = dict(PRTK=100, RTKM=200, SIBN=300)
    port = portfolio.Portfolio("2018-12-17", 1000, pos)
    metrics3 = metrics.Metrics(port, months=3)
    metrics12 = metrics.Metrics(port, months=12)
    assert metrics12.std_gradient == pytest.approx(metrics12.std[PORTFOLIO])
    assert metrics3.std_gradient == pytest.approx(metrics12.std[PORTFOLIO] / 2)
    assert metrics3.std_gradient == pytest.approx(metrics3.std[PORTFOLIO] / 2)


def test_forecast_func(monkeypatch):
    monkeypatch.setattr(config, "ML_PARAMS", ML_PARAMS)
    pos = dict(SIBN=300, PRTK=100, RTKM=200)
    port = portfolio.Portfolio("2018-12-17", 1000, pos)
    result = metrics.Metrics(port)
    # noinspection PyProtectedMember
    forecast = result._forecast_func()
    assert isinstance(forecast, Forecast)
    assert forecast.date == pd.Timestamp("2018-12-17")
    assert forecast.tickers == ("PRTK", "RTKM", "SIBN")
    assert forecast.shrinkage == pytest.approx(0.6972112123349591)
