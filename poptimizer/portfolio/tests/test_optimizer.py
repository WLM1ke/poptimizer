import pandas as pd
import pytest

from poptimizer import portfolio, config
from poptimizer.portfolio import optimizer

ML_PARAMS = {
    "data": (
        ("Label", {"days": 30}),
        ("STD", {"days": 252}),
        ("Ticker", {"on_off": False}),
        ("Mom12m", {"days": 252}),
        ("DivYield", {"days": 252}),
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


@pytest.fixture(name="opt")
def make_optimizer(monkeypatch):
    monkeypatch.setattr(config, "ML_PARAMS", ML_PARAMS)
    monkeypatch.setattr(config, "TURNOVER_CUT_OFF", 0.0016)
    date = pd.Timestamp("2018-12-17")
    positions = dict(
        KZOS=800, MGNT=0, PIKK=800, MSTT=0, MTLRP=0, GMKN=21, CBOM=0, SNGSP=13000
    )
    port = portfolio.Portfolio(date, 1000, positions)
    return optimizer.Optimizer(port, months=11)


def test_best_sell(opt):
    assert opt.best_sell == "SNGSP"


def test_gradient_growth(opt):
    grad = opt.metrics.gradient
    growth = opt.gradient_growth
    assert grad["KZOS"] > grad["CBOM"]
    assert growth["KZOS"] == pytest.approx(0.30868794294740187)


def test_best_buy(opt):
    assert opt.best_buy == "KZOS"


def test_main_stat(opt):
    # noinspection PyProtectedMember
    df = opt._main_stat()
    assert isinstance(df, pd.DataFrame)
    assert df.shape == (10, 4)
    assert (df.columns == ["LOWER_BOUND", "GRADIENT", "TURNOVER", "GROWTH"]).all()
    assert df.index[0] == "KZOS"
    assert df.index[-1] == "MGNT"


def test_trade_recommendation(opt):
    # noinspection PyProtectedMember
    rec = opt._trade_recommendation()
    assert isinstance(rec, str)
    assert "Продать SNGSP" in rec
    assert "Купить  KZOS" in rec


def test_str(opt):
    text = str(opt)
    assert "ОПТИМИЗАЦИЯ ПОРТФЕЛЯ" in text
