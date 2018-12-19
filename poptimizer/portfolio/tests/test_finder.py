import pandas as pd
import pytest

from poptimizer import portfolio
from poptimizer.ml import feature
from poptimizer.portfolio import finder


def test_feature_days():
    assert finder.feature_days(feature.Label) == 21


def test_get_turnover():
    date = pd.Timestamp("2018-12-18")
    positions = dict(TATN=20000, KZOS=20000, LKOH=20000)
    port = portfolio.Portfolio(date, 0, positions)
    df = finder.get_turnover(port, ("KZOS", "AKRN"))
    assert isinstance(df, pd.Series)
    assert df.size == 4
    assert df["KZOS"] == pytest.approx(0.986873)


def test_find_momentum(capsys):
    date = pd.Timestamp("2018-12-18")
    positions = dict(TATN=20000, KZOS=20000, LKOH=20000)
    port = portfolio.Portfolio(date, 0, positions)
    finder.find_momentum(port, 0.02)
    captured = capsys.readouterr()
    assert "Выведены 2% - 5 акций" in captured.out
    assert "TATN   0.509073  0.244496  1.000000  2.082128     " in captured.out
    assert "BANEP  0.412600  0.205033  0.999980  2.012322  ADD" in captured.out
    assert "NVTK   0.536663  0.275343  1.000000  1.949073  ADD" in captured.out
    assert "KZOS   0.385195  0.199113  0.986873  1.909157     " in captured.out
    assert "SIBN   0.418839  0.240944  0.999999  1.738323  ADD" in captured.out
    assert "LKOH" not in captured.out


def test_find_dividends(capsys):
    date = pd.Timestamp("2018-12-18")
    positions = dict(CHMF=20000, TATN=20000, KZOS=20000, LKOH=20000)
    port = portfolio.Portfolio(date, 0, positions)
    df = finder.find_dividends(port, 0.02)
    captured = capsys.readouterr()
    assert "CHMF    0.142110  1.000000  0.142110     " in captured.out
    assert "MTLRP   0.142030  0.999910  0.142018  ADD" in captured.out
    assert isinstance(df, pd.DataFrame)
    assert df.shape == (5, 4)
    assert list(df.columns) == ["Dividends", "TURNOVER", "SCORE", "ADD"]
    assert list(df.index) == ["CHMF", "MTLRP", "LSNGP", "ENRU", "TATNP"]


def test_find_zero_turnover_and_weight():
    date = pd.Timestamp("2018-12-18")
    positions = dict(KAZT=1, KAZTP=0, CHMF=20000, TATN=20000, KZOS=20000, LKOH=20000)
    port = portfolio.Portfolio(date, 0, positions)
    tickers = finder.find_zero_turnover_and_weight(port)
    assert "KAZT" not in tickers
    assert "KAZTP" in tickers
