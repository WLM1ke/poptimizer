import pandas as pd
import pytest

from poptimizer import portfolio, config
from poptimizer.portfolio import finder


def test_get_turnover(monkeypatch):
    monkeypatch.setattr(config, "TURNOVER_FACTOR", 200)
    date = pd.Timestamp("2018-12-18")
    positions = dict(TATN=20000, KZOS=20000, LKOH=20000)
    port = portfolio.Portfolio(date, 0, positions)
    df = finder.get_turnover(port, ("KZOS", "AKRN"))
    assert isinstance(df, pd.Series)
    assert df.size == 4
    assert df["KZOS"] == pytest.approx(0.5476826158633951)


def test_find_good_volume():
    date = pd.Timestamp("2018-12-18")
    positions = dict(KAZT=1, KAZTP=0, CHMF=20000, TATN=20000, KZOS=20000, LKOH=20000)
    port = portfolio.Portfolio(date, 0, positions)
    df = finder.find_good_volume(port)
    assert df.columns.to_list() == ["VOLUME", "ADD"]
    assert len(df) > 50
    assert df.loc["CHMF", "ADD"] == ""
    assert df.loc["SBER", "ADD"] == "ADD"
    assert df["VOLUME"].min() > 0
    assert "GAZP" in df.index
    assert "TTLK" not in df.index


def test_find_zero_turnover_and_weight():
    date = pd.Timestamp("2018-12-18")
    positions = dict(KAZT=1, KAZTP=0, CHMF=20000, TATN=20000, KZOS=20000, LKOH=20000)
    port = portfolio.Portfolio(date, 0, positions)
    tickers = finder.find_zero_turnover_and_weight(port)
    assert "KAZT" not in tickers
    assert "KAZTP" in tickers


def test_add_tickers(capsys):
    date = pd.Timestamp("2018-12-19")
    positions = dict(KAZT=1, KAZTP=0, CHMF=20000, TATN=20000, KZOS=20000, LKOH=20000)
    port = portfolio.Portfolio(date, 0, positions)
    finder.add_tickers(port)
    captured = capsys.readouterr()
    assert "ДОСТАТОЧНЫЙ ОБОРОТ" in captured.out


def test_remove_tickers(capsys):
    date = pd.Timestamp("2018-12-19")
    positions = dict(KAZT=1, KAZTP=0, CHMF=20000, TATN=20000, KZOS=20000, LKOH=20000)
    port = portfolio.Portfolio(date, 0, positions)
    finder.remove_tickers(port)
    captured = capsys.readouterr()
    assert "БУМАГИ С НУЛЕВЫМ ОБОРОТОМ И ВЕСОМ" in captured.out
