import numpy as np
import pandas as pd
import pytest

from poptimizer import config
from poptimizer.data import div
from poptimizer.portfolio import Portfolio, portfolio, metrics
from poptimizer.portfolio.metrics import Metrics, Forecast
from poptimizer.portfolio.portfolio import CASH, PORTFOLIO

ML_PARAMS = {
    "data": (
        ("Label", {"days": 89, "div_share": 0.3, "on_off": True}),
        ("Scaler", {"days": 238, "on_off": True}),
        ("Ticker", {"on_off": True}),
        ("Mom12m", {"days": 187, "on_off": True, "periods": 2}),
        ("DivYield", {"days": 263, "on_off": True, "periods": 2}),
        ("Mom1m", {"days": 36, "on_off": False}),
        ("RetMax", {"days": 48, "on_off": True}),
        ("ChMom6m", {"days": 99, "on_off": True}),
        ("STD", {"days": 24, "on_off": True}),
        ("DayOfYear", {"on_off": False}),
    ),
    "model": {
        "bagging_temperature": 0.491_539_233_402_797_54,
        "depth": 16,
        "l2_leaf_reg": 0.588_094_083_563_754_5,
        "learning_rate": 0.005_422_182_747_620_653,
        "one_hot_max_size": 2,
        "random_strength": 1.063_218_585_772_184_5,
    },
}


@pytest.fixture(scope="function", autouse=True)
def set_stats_start(monkeypatch):
    monkeypatch.setattr(div, "STATS_START", pd.Timestamp("2010-01-01"))
    yield


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
    assert np.allclose(mean, [1, 2, 3, 0, 1.832_871_915_473_98])


def test_std(metrics_and_index):
    metrics, index = metrics_and_index
    std = metrics.std

    assert isinstance(std, pd.Series)
    # noinspection PyUnresolvedReferences
    assert (std.index == index).all()
    assert np.allclose(std, [3, 2, 1, 0, 1.409_798_518_537_9])


def test_beta(metrics_and_index):
    metrics, index = metrics_and_index
    beta = metrics.beta

    assert isinstance(beta, pd.Series)
    # noinspection PyUnresolvedReferences
    assert (beta.index == index).all()
    assert np.allclose(
        beta, [1.632_231_214_983_82, 1.310_819_128_179_28, 0.323_000_567_807_792, 0, 1]
    )


def test_lower_bound(metrics_and_index):
    metrics, index = metrics_and_index
    lower_bound = metrics.lower_bound

    assert isinstance(lower_bound, pd.Series)
    # noinspection PyUnresolvedReferences
    assert (lower_bound.index == index).all()
    assert np.allclose(
        lower_bound,
        [
            -2.051_117_148_795_5,
            -1.347_990_864_978_29,
            0.294_634_278_017_675,
            0,
            -0.951_580_539_669_401,
        ],
    )


def test_gradient(metrics_and_index):
    metrics, index = metrics_and_index
    gradient = metrics.gradient

    assert isinstance(gradient, pd.Series)
    # noinspection PyUnresolvedReferences
    assert (gradient.index == index).all()
    assert np.allclose(
        gradient,
        [
            -1.099_536_609_126_1,
            -0.396_410_325_308_889,
            1.246_214_817_687_08,
            0.951_580_539_669_401,
            0,
        ],
    )


def test_str(metrics_and_index):
    met, _ = metrics_and_index
    assert "КЛЮЧЕВЫЕ МЕТРИКИ ПОРТФЕЛЯ" in str(met)


def test_std_gradient():
    pos = dict(AKRN=709, PRTK=100, RTKM=200, SIBN=300)
    port = portfolio.Portfolio("2018-12-17", 1000, pos)
    metrics3 = metrics.Metrics(port, months=3)
    metrics12 = metrics.Metrics(port, months=12)
    assert metrics12.std_gradient == pytest.approx(metrics12.std[PORTFOLIO])
    assert metrics3.std_gradient == pytest.approx(metrics12.std[PORTFOLIO] / 2)
    assert metrics3.std_gradient == pytest.approx(metrics3.std[PORTFOLIO] / 2)


def test_forecast_func(monkeypatch):
    monkeypatch.setattr(config, "ML_PARAMS", ML_PARAMS)
    pos = dict(AKRN=709, PRTK=100, RTKM=200, SIBN=300)
    port = portfolio.Portfolio("2018-12-17", 1000, pos)
    result = metrics.Metrics(port)
    # noinspection PyProtectedMember
    forecast = result._forecast_func()
    assert isinstance(forecast, Forecast)
    assert forecast.date == pd.Timestamp("2018-12-17")
    assert forecast.tickers == ("AKRN", "PRTK", "RTKM", "SIBN")
    assert forecast.shrinkage == pytest.approx(0.987_081_025_464_832_8)
