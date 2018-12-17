import numpy as np
import pandas as pd
import pytest

from poptimizer.portfolio import Portfolio
from poptimizer.portfolio.metrics import AbstractMetrics, Forecast
from poptimizer.portfolio.portfolio import CASH, PORTFOLIO


class SimpleMetrics(AbstractMetrics):
    def _forecast_func(self):
        mean = np.array([1.0, 2.0, 3.0])
        cov = np.array([[9.0, 3.0, 1.0], [3.0, 4.0, 0.5], [1.0, 0.5, 1.0]])
        portfolio = self._portfolio
        return Forecast(
            portfolio.date,
            tuple(portfolio.index[:-2]),
            mean,
            cov,
            pd.Series(),
            0.0,
            0.0,
            0.0,
        )


@pytest.fixture(scope="module", name="metrics_and_index")
def create_metrics_and_index():
    date = "2018-12-10"
    positions = dict(LSNGP=161, MSTT=505, PIKK=57)
    portfolio = Portfolio(date, 10000, positions)
    metrics = SimpleMetrics(portfolio, 3)
    index = pd.Index(["LSNGP", "MSTT", "PIKK", CASH, PORTFOLIO])
    return metrics, index


# noinspection PyUnresolvedReferences
def test_mean(metrics_and_index):
    metrics, index = metrics_and_index
    mean = metrics.mean

    assert isinstance(mean, pd.Series)
    assert (mean.index == index).all()
    assert np.allclose(mean, [1, 2, 3, 0, 1.83287191547398])


# noinspection PyUnresolvedReferences
def test_std(metrics_and_index):
    metrics, index = metrics_and_index
    std = metrics.std

    assert isinstance(std, pd.Series)
    assert (std.index == index).all()
    assert np.allclose(std, [3, 2, 1, 0, 1.4097985185379])


# noinspection PyUnresolvedReferences
def test_beta(metrics_and_index):
    metrics, index = metrics_and_index
    beta = metrics.beta

    assert isinstance(beta, pd.Series)
    assert (beta.index == index).all()
    assert np.allclose(
        beta, [1.63223121498382, 1.31081912817928, 0.323000567807792, 0, 1]
    )


# noinspection PyUnresolvedReferences
def test_lower_bound(metrics_and_index):
    metrics, index = metrics_and_index
    lower_bound = metrics.lower_bound

    assert isinstance(lower_bound, pd.Series)
    assert (lower_bound.index == index).all()
    assert np.allclose(
        lower_bound,
        [-2.0511171487955, -1.34799086497829, 0.294634278017675, 0, -0.951580539669401],
    )


# noinspection PyUnresolvedReferences
def test_gradient(metrics_and_index):
    metrics, index = metrics_and_index
    gradient = metrics.gradient

    assert isinstance(gradient, pd.Series)
    assert (gradient.index == index).all()
    assert np.allclose(
        gradient,
        [-1.0995366091261, -0.396410325308889, 1.24621481768708, 0.951580539669401, 0],
    )


def test_str(metrics_and_index):
    metrics, _ = metrics_and_index
    assert "КЛЮЧЕВЫЕ МЕТРИКИ ПОРТФЕЛЯ" in str(metrics)
