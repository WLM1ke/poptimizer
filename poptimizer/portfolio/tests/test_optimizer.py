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
    assert df.shape == (5, 7)
    assert list(df.columns) == ["SELL", "Q_SELL", "BUY", "Q_BUY", "GRAD_DIFF", "TURNOVER", "P_VALUE"]

    wilcoxon = stats.wilcoxon([1] * 20, alternative="greater", correction=True)[1] * 17

    assert df.loc[1, "SELL"] == "MTSS"
    assert df.loc[1, "BUY"] == "KZOS"
    assert df.loc[1, "P_VALUE"] == pytest.approx(wilcoxon)

    assert df.loc[2, "SELL"] == "RTKMP"
    assert df.loc[2, "BUY"] == "KZOS"
    assert df.loc[2, "P_VALUE"] == pytest.approx(wilcoxon)

    assert df.loc[3, "SELL"] == "MTSS"
    assert df.loc[3, "BUY"] == "RTKMP"
    assert df.loc[3, "P_VALUE"] == pytest.approx(wilcoxon)


def test_str(opt):
    assert "ОПТИМИЗАЦИЯ ПОРТФЕЛЯ" in str(opt)
