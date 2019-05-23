import pandas as pd
import pytest

from poptimizer import portfolio, config, optimizer
from poptimizer.portfolio import finder

ML_PARAMS = {
    "data": (
        ("Label", {"days": 21}),
        ("STD", {"days": 252}),
        ("Ticker", {}),
        ("Mom12m", {"days": 252, "periods": 1}),
        ("DivYield", {"days": 252}),
        ("Mom1m", {"on_off": False, "days": 21}),
    ),
    "model": {
        "bagging_temperature": 1,
        "depth": 6,
        "l2_leaf_reg": 3,
        "learning_rate": 0.1,
        "one_hot_max_size": 2,
        "random_strength": 1,
        "ignored_features": [],
    },
}


def test_feature_params(monkeypatch):
    monkeypatch.setattr(config, "ML_PARAMS", ML_PARAMS)
    assert finder.feature_params("Mom1m") == {"on_off": False, "days": 21}


def test_get_turnover(monkeypatch):
    monkeypatch.setattr(config, "TURNOVER_CUT_OFF", 0.0012)
    monkeypatch.setattr(config, "TURNOVER_PERIOD", 21)
    date = pd.Timestamp("2018-12-18")
    positions = dict(TATN=20000, KZOS=20000, LKOH=20000)
    port = portfolio.Portfolio(date, 0, positions)
    df = finder.get_turnover(port, ("KZOS", "AKRN"))
    assert isinstance(df, pd.Series)
    assert df.size == 4
    assert df["KZOS"] == pytest.approx(0.986873)


def test_find_momentum(monkeypatch):
    monkeypatch.setattr(config, "TURNOVER_CUT_OFF", 0.0022)
    monkeypatch.setattr(config, "TURNOVER_PERIOD", 21 * 2)
    monkeypatch.setattr(finder, "feature_params", lambda x: {"days": 252, "periods": 1})
    date = pd.Timestamp("2018-12-18")
    positions = dict(TATN=20000, KZOS=20000, LKOH=20000)
    port = portfolio.Portfolio(date, 0, positions)
    df = finder.find_momentum(port, 0.02)
    assert isinstance(df, pd.DataFrame)
    assert df.shape == (5, 5)
    assert list(df.columns) == ["Mom12m_0", "STD", "TURNOVER", "_DRAW_DOWN", "ADD"]
    assert list(df.index) == ["AKRN", "RTKMP", "BANEP", "KZOS", "CBOM"]
    assert df.loc["AKRN", "ADD"] == "ADD"
    assert df.loc["KZOS", "ADD"] == ""
    assert df.loc["BANEP", "ADD"] == "ADD"


def test_find_dividends(monkeypatch):
    monkeypatch.setattr(config, "TURNOVER_CUT_OFF", 0.0022)
    monkeypatch.setattr(config, "ML_PARAMS", ML_PARAMS)
    date = pd.Timestamp("2018-12-18")
    positions = dict(CHMF=20000, TATN=20000, KZOS=20000, LKOH=20000)
    port = portfolio.Portfolio(date, 0, positions)
    df = finder.find_dividends(port, 0.02)
    assert isinstance(df, pd.DataFrame)
    assert df.shape == (5, 4)
    assert list(df.columns) == ["DivYield_0", "TURNOVER", "SCORE", "ADD"]
    assert list(df.index) == ["CHMF", "MTLRP", "MRKV", "MRKP", "LSNGP"]
    assert df.loc["CHMF", "ADD"] == ""
    assert df.loc["MTLRP", "ADD"] == "ADD"


def test_find_zero_turnover_and_weight():
    date = pd.Timestamp("2018-12-18")
    positions = dict(KAZT=1, KAZTP=0, CHMF=20000, TATN=20000, KZOS=20000, LKOH=20000)
    port = portfolio.Portfolio(date, 0, positions)
    tickers = finder.find_zero_turnover_and_weight(port)
    assert "KAZT" not in tickers
    assert "KAZTP" in tickers


def test_find_low_gradient(monkeypatch):
    monkeypatch.setattr(config, "ML_PARAMS", ML_PARAMS)
    date = pd.Timestamp("2018-12-19")
    positions = dict(
        AKRN=563,
        BANE=236,
        CHMF=2000,
        BANEP=1644,
        KAZT=0,
        KAZTP=0,
        KZOS=3400,
        LKOH=270,
        TATN=420,
        MGNT=0,
        MTLRP=0,
    )
    port = portfolio.Portfolio(date, 0, positions)
    opt = optimizer.Optimizer(port, months=11)
    bad_tickers = finder.find_low_gradient(opt)
    assert len(bad_tickers) == 1


def test_add_tickers(capsys):
    date = pd.Timestamp("2018-12-19")
    positions = dict(KAZT=1, KAZTP=0, CHMF=20000, TATN=20000, KZOS=20000, LKOH=20000)
    port = portfolio.Portfolio(date, 0, positions)
    finder.add_tickers(port)
    captured = capsys.readouterr()
    assert "МОМЕНТУМ ТИКЕРЫ" in captured.out
    assert "ДИВИДЕНДНЫЕ ТИКЕРЫ" in captured.out


def test_remove_tickers(capsys):
    date = pd.Timestamp("2018-12-19")
    positions = dict(KAZT=1, KAZTP=0, CHMF=20000, TATN=20000, KZOS=20000, LKOH=20000)
    port = portfolio.Portfolio(date, 0, positions)
    opt = optimizer.Optimizer(port, months=11)
    finder.remove_tickers(opt)
    captured = capsys.readouterr()
    assert "БУМАГИ С НУЛЕВЫМ ОБОРОТОМ И ВЕСОМ" in captured.out
    assert "БУМАГИ С НИЗКИМ ГРАДИЕНТОМ" in captured.out
