import pandas as pd
import pytest

from poptimizer import portfolio, config
from poptimizer.portfolio import returns
from poptimizer.portfolio.metrics import Forecast
from poptimizer.portfolio.portfolio import PORTFOLIO

ML_PARAMS = (
    (
        (True, {"days": 30}),
        (True, {"days": 252}),
        (False, {}),
        (True, {"days": 252}),
        (True, {"days": 252}),
    ),
    {
        "bagging_temperature": 1.16573715129796,
        "depth": 4,
        "l2_leaf_reg": 2.993522023941868,
        "learning_rate": 0.10024901894125209,
        "one_hot_max_size": 100,
        "random_strength": 0.9297802156425078,
        "ignored_features": [1],
    },
)


def test_std_gradient():
    pos = dict(PRTK=100, RTKM=200, SIBN=300)
    port = portfolio.Portfolio("2018-12-17", 1000, pos)
    metrics3 = returns.ReturnsMetrics(port, months=3)
    metrics12 = returns.ReturnsMetrics(port, months=12)
    assert metrics12.std_gradient == pytest.approx(metrics12.std[PORTFOLIO])
    assert metrics3.std_gradient == pytest.approx(metrics12.std[PORTFOLIO] / 2)
    assert metrics3.std_gradient == pytest.approx(metrics3.std[PORTFOLIO] / 2)


def test_forecast_func(monkeypatch):
    monkeypatch.setattr(config, "ML_PARAMS", ML_PARAMS)
    pos = dict(SIBN=300, PRTK=100, RTKM=200)
    port = portfolio.Portfolio("2018-12-17", 1000, pos)
    metrics = returns.ReturnsMetrics(port)
    # noinspection PyProtectedMember
    forecast = metrics._forecast_func()
    assert isinstance(forecast, Forecast)
    assert forecast.date == pd.Timestamp("2018-12-17")
    assert forecast.tickers == ("PRTK", "RTKM", "SIBN")
    assert forecast.shrinkage == pytest.approx(0.6972112123349591)
