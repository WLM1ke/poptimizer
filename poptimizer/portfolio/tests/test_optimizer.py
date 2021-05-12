import pandas as pd
import pytest
from scipy import stats

from poptimizer.portfolio import Portfolio, optimizer, portfolio


class FakeMetricsResample:
    def __init__(self, _=None):
        self.count = 20

    @property
    def all_gradients(self):
        grad = dict(CHEP=0.015, KZOS=0.20, MTSS=0.01, RTKMP=0.03, TRCN=0.04, CASH=-0.05, PORTFOLIO=0.0)
        return pd.DataFrame([grad] * 20).T

    @property
    def beta(self):
        beta = dict(CHEP=0.1, KZOS=0.5, MTSS=1.0, RTKMP=1.5, TRCN=2.0, CASH=0, PORTFOLIO=1.0)
        return pd.Series(beta)


@pytest.fixture(scope="module", name="opt")
def make_opt():
    cash = 176
    positions = dict(CHEP=0, KZOS=5080 * 2, MTSS=3300 * 2, RTKMP=29400 * 2, TRCN=68 * 2)
    date = "2020-05-13"
    port = Portfolio(date, cash, positions)

    saved_metrics = optimizer.metrics.MetricsResample
    optimizer.metrics.MetricsResample = FakeMetricsResample

    yield optimizer.Optimizer(port)

    optimizer.metrics.MetricsResample = saved_metrics


def test_trials(opt):
    assert opt.trials == 4 + 4 + 4 + 5


def test_best_combination(opt, monkeypatch):
    monkeypatch.setattr(optimizer, "COSTS", 0)
    monkeypatch.setattr(portfolio, "MAX_HISTORY", 100)
    monkeypatch.setattr(portfolio, "ADD_DAYS", 100)
    df = opt.best_combination

    assert isinstance(df, pd.DataFrame)
    assert df.shape == (2, 6)
    assert list(df.columns) == [
        "SELL",
        "BUY",
        "RISK_CON",
        "R_DIFF",
        "TURNOVER",
        "P_VALUE",
    ]

    assert df.loc[1, "SELL"] == "MTSS"
    assert df.loc[1, "BUY"] == "KZOS"

    assert df.loc[2, "SELL"] == "TRCN"
    assert df.loc[2, "BUY"] == "KZOS"


def test_str(opt):
    assert "ОПТИМИЗАЦИЯ ПОРТФЕЛЯ" in str(opt)
