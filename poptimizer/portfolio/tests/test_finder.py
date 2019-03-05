import pandas as pd
import pytest

from poptimizer import portfolio, config, optimizer
from poptimizer.ml import feature_old, examples_old
from poptimizer.portfolio import finder

ML_PARAMS = (
    (
        (True, {"days": 21}),
        (True, {"days": 252}),
        (True, {}),
        (True, {"days": 252}),
        (True, {"days": 252}),
        (False, {"days": 21}),
    ),
    {
        "bagging_temperature": 1,
        "depth": 6,
        "l2_leaf_reg": 3,
        "learning_rate": 0.1,
        "one_hot_max_size": 2,
        "random_strength": 1,
        "ignored_features": [],
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


def test_feature_days(monkeypatch):
    monkeypatch.setattr(config, "ML_PARAMS", ML_PARAMS)
    assert finder.feature_days(feature_old.Label) == 21


# noinspection PyUnresolvedReferences
def test_get_turnover(monkeypatch):
    monkeypatch.setattr(config, "TURNOVER_CUT_OFF", 0.0012)
    date = pd.Timestamp("2018-12-18")
    positions = dict(TATN=20000, KZOS=20000, LKOH=20000)
    port = portfolio.Portfolio(date, 0, positions)
    df = finder.get_turnover(port, ("KZOS", "AKRN"))
    assert isinstance(df, pd.Series)
    assert df.size == 4
    assert df["KZOS"] == pytest.approx(0.986873)


# noinspection PyUnresolvedReferences
def test_find_momentum(monkeypatch):
    monkeypatch.setattr(config, "TURNOVER_CUT_OFF", 0.0022)
    monkeypatch.setattr(finder, "feature_days", lambda x: 252)
    date = pd.Timestamp("2018-12-18")
    positions = dict(TATN=20000, KZOS=20000, LKOH=20000)
    port = portfolio.Portfolio(date, 0, positions)
    df = finder.find_momentum(port, 0.02)
    assert isinstance(df, pd.DataFrame)
    assert df.shape == (5, 5)
    assert list(df.columns) == ["Mom12m", "STD", "TURNOVER", "T_SCORE", "ADD"]
    assert list(df.index) == ["TATN", "BANEP", "NVTK", "KZOS", "SIBN"]
    assert df.loc["TATN", "ADD"] == ""
    assert df.loc["KZOS", "ADD"] == ""
    assert df.loc["BANEP", "ADD"] == "ADD"


# noinspection PyUnresolvedReferences
def test_find_dividends(monkeypatch):
    monkeypatch.setattr(config, "TURNOVER_CUT_OFF", 0.0022)
    monkeypatch.setattr(config, "ML_PARAMS", ML_PARAMS)
    date = pd.Timestamp("2018-12-18")
    positions = dict(CHMF=20000, TATN=20000, KZOS=20000, LKOH=20000)
    port = portfolio.Portfolio(date, 0, positions)
    df = finder.find_dividends(port, 0.02)
    assert isinstance(df, pd.DataFrame)
    assert df.shape == (5, 4)
    assert list(df.columns) == ["DivYield", "TURNOVER", "SCORE", "ADD"]
    assert list(df.index) == ["CHMF", "MTLRP", "MRKV", "MRKP", "LSNGP"]
    assert df.loc["CHMF", "ADD"] == ""
    assert df.loc["MTLRP", "ADD"] == "ADD"


# noinspection PyUnresolvedReferences
def test_find_zero_turnover_and_weight():
    date = pd.Timestamp("2018-12-18")
    positions = dict(KAZT=1, KAZTP=0, CHMF=20000, TATN=20000, KZOS=20000, LKOH=20000)
    port = portfolio.Portfolio(date, 0, positions)
    tickers = finder.find_zero_turnover_and_weight(port)
    assert "KAZT" not in tickers
    assert "KAZTP" in tickers


# noinspection PyUnresolvedReferences
def test_find_low_gradient(monkeypatch):
    monkeypatch.setattr(examples_old.Examples, "FEATURES", FEATURES)
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
    assert "MGNT" in bad_tickers


def test_add_tickers(capsys):
    # noinspection PyUnresolvedReferences
    date = pd.Timestamp("2018-12-19")
    positions = dict(KAZT=1, KAZTP=0, CHMF=20000, TATN=20000, KZOS=20000, LKOH=20000)
    port = portfolio.Portfolio(date, 0, positions)
    finder.add_tickers(port)
    captured = capsys.readouterr()
    assert "МОМЕНТУМ ТИКЕРЫ" in captured.out
    assert "ДИВИДЕНДНЫЕ ТИКЕРЫ" in captured.out


def test_remove_tickers(capsys):
    # noinspection PyUnresolvedReferences
    date = pd.Timestamp("2018-12-19")
    positions = dict(KAZT=1, KAZTP=0, CHMF=20000, TATN=20000, KZOS=20000, LKOH=20000)
    port = portfolio.Portfolio(date, 0, positions)
    opt = optimizer.Optimizer(port, months=11)
    finder.remove_tickers(opt)
    captured = capsys.readouterr()
    assert "БУМАГИ С НУЛЕВЫМ ОБОРОТОМ И ВЕСОМ" in captured.out
    assert "БУМАГИ С НИЗКИМ ГРАДИЕНТОМ" in captured.out
