import pandas as pd
import pytest
from scipy import stats

from poptimizer import Portfolio
from poptimizer.portfolio import optimizer


class FakeMetricsResample:
    def __init__(self, _=None):
        self.count = 9

    @property
    def gradient(self):
        grad = dict(
            CHEP=0.01,
            KZOS=0.11,
            MTSS=-0.03,
            RTKMP=-0.06,
            TRCN=-0.10,
            CASH=-0.14,
            PORTFOLIO=0.0,
        )
        return pd.Series(grad, name="GRAD")

    @property
    def error(self):
        grad = dict(
            CHEP=0.01,
            KZOS=0.02,
            MTSS=0.01,
            RTKMP=0.03,
            TRCN=0.02,
            CASH=0.01,
            PORTFOLIO=0.0,
        )
        return pd.Series(grad, name="ERROR")


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


def test_adj_gradient(opt):
    adj_gradient = opt.adj_gradient
    assert isinstance(adj_gradient, pd.Series)
    assert len(adj_gradient) == 7
    assert adj_gradient.name == "ADJ_GRAD"

    assert adj_gradient["CHEP"] == 0.01
    assert adj_gradient["KZOS"] < 0.11
    assert adj_gradient["KZOS"] == 0.11 * opt.portfolio.turnover_factor["KZOS"]
    assert adj_gradient["MTSS"] == -0.03
    assert adj_gradient["RTKMP"] == -0.06
    assert adj_gradient["TRCN"] == -0.10
    assert adj_gradient["CASH"] == -0.14
    assert adj_gradient["PORTFOLIO"] == 0


def test_t_score(opt):
    assert opt.t_score == stats.t.ppf(0.975, 8)


def test_trials(opt):
    assert opt.trials == 6


def test_t_score_bonferroni(opt):
    assert opt.t_score_bonferroni == stats.t.ppf(1 - 0.025 / 6, 8)


def test_lower_bound(opt):
    lower_bound = opt.lower_bound
    assert isinstance(lower_bound, pd.Series)
    assert len(lower_bound) == 7
    assert lower_bound.name == "LOWER"

    t = opt.t_score_bonferroni

    assert lower_bound["CHEP"] == 0.01 - t * 0.01
    assert (
        lower_bound["KZOS"] == 0.11 * opt.portfolio.turnover_factor["KZOS"] - t * 0.02
    )
    assert lower_bound["MTSS"] == -0.03 - t * 0.01
    assert lower_bound["RTKMP"] == -0.06 - t * 0.03
    assert lower_bound["TRCN"] == -0.10 - t * 0.02
    assert lower_bound["CASH"] == -0.14 - t * 0.01
    assert lower_bound["PORTFOLIO"] == 0.0


def test_upper_bound(opt):
    upper_bound = opt.upper_bound
    assert isinstance(upper_bound, pd.Series)
    assert len(upper_bound) == 7
    assert upper_bound.name == "UPPER"

    t = opt.t_score_bonferroni

    assert upper_bound["CHEP"] == 0.01 + t * 0.01
    assert (
        upper_bound["KZOS"] == 0.11 * opt.portfolio.turnover_factor["KZOS"] + t * 0.02
    )
    assert upper_bound["MTSS"] == -0.03 + t * 0.01
    assert upper_bound["RTKMP"] == -0.06 + t * 0.03
    assert upper_bound["TRCN"] == -0.10 + t * 0.02
    assert upper_bound["CASH"] == -0.14 + t * 0.01
    assert upper_bound["PORTFOLIO"] == 0.0


def test_buy_sell(opt):
    buy_sell = opt.buy_sell
    assert isinstance(buy_sell, pd.Series)
    assert len(buy_sell) == 7
    assert buy_sell.name == "BUY_SELL"

    assert buy_sell["CHEP"] == 0
    assert buy_sell["KZOS"] == 1
    assert buy_sell["MTSS"] == 0
    assert buy_sell["RTKMP"] == 0
    assert buy_sell["TRCN"] == -3
    assert buy_sell["CASH"] == 0
    assert buy_sell["PORTFOLIO"] == 0.0


def test_str(opt):
    assert "ОПТИМИЗАЦИЯ ПОРТФЕЛЯ" in str(opt)
