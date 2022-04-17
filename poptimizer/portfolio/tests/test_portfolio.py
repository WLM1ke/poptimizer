import logging
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from poptimizer.config import POptimizerError
from poptimizer.portfolio import portfolio
from poptimizer.portfolio.portfolio import CASH, PORTFOLIO

PARAMS = dict(
    name=["test"],
    date="2018-03-19",
    cash=1000,
    positions=dict(GAZP=6820, VSMO=145, TTLK=1_230_000),
    value=3_699_111,
)


@pytest.fixture(scope="module", name="port")
def make_portfolio():
    return portfolio.Portfolio(**PARAMS)


def test_portfolio(monkeypatch, port):
    monkeypatch.setattr(portfolio, "LIQUIDITY_DAYS", 100)

    assert "ПОРТФЕЛЬ [test] - 2018-03-19" in str(port)
    assert port.date == pd.Timestamp("2018-03-19")
    assert port.index.tolist() == ["GAZP", "TTLK", "VSMO", CASH, PORTFOLIO]
    assert np.allclose(port.shares, [6820, 1_230_000, 145, 1000, 1])
    assert np.allclose(port.lot_size, [10, 1000, 1, 1, 1])
    assert np.allclose(port.lots, [682, 1230, 145, 1000, 1])
    assert np.allclose(port.price, [139.91, 0.1525, 17630, 1, 3_699_111])
    assert np.allclose(port.value, [954_186, 187_575, 2_556_350, 1000, 3_699_111])
    assert np.allclose(
        port.weight,
        [0.257_950_085_844_95, 0.050_708_129_601_95, 0.691_071_449_329_312, 0.000_270_335_223_788, 1],
    )
    assert np.allclose(port.turnover_factor, [1006.594863, 0.007234170197424721, 0.844742, 1007.446839, 1007.446839])


def test_portfolio_wrong_value():
    with pytest.raises(POptimizerError) as error:
        PARAMS["value"] = 123
        portfolio.Portfolio(**PARAMS)
    assert "Введенная стоимость портфеля 123" in str(error.value)


def fake_securities_with_reg_number():
    return pd.Index(["SBER", "SBERP"])


def test_load_from_yaml(monkeypatch):
    monkeypatch.setattr(portfolio.config, "PORT_PATH", Path(__file__).parent)
    port = portfolio.load_from_yaml("2020-06-22")

    assert isinstance(port, portfolio.Portfolio)
    assert port.date == pd.Timestamp("2020-06-22")
    print(port.value[PORTFOLIO])
    assert list(port.index[:-2]) == ["AKRN", "GMKN", "VSMO"]
    assert port.shares["AKRN"] == 1
    assert port.shares["GMKN"] == 5
    assert port.shares["VSMO"] == 4
    assert port.shares["CASH"] == 369.02


def test_load_tickers(monkeypatch):
    monkeypatch.setattr(portfolio.config, "PORT_PATH", Path(__file__).parent)
    tickers = portfolio.load_tickers()

    assert isinstance(tickers, tuple)
    assert tickers == ("AKRN", "GMKN", "VSMO")
