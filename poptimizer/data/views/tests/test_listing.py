"""Тесты для данных о торгуемых бумагах."""
import pandas as pd
import pytest

from poptimizer.data.views import listing

ALL_HISTORY_CASES = (
    (
        ("AKRN", "GAZP"),
        "2021-12-30",
        "2022-01-07",
        5,
    ),
    (
        ("AKRN", "GAZP"),
        "2021-12-31",
        "2022-01-07",
        4,
    ),
    (
        ("AKRN", "GAZP", "T-RM"),
        "2021-12-30",
        "2022-01-07",
        6,
    ),
    (
        ("AKRN", "GAZP", "T-RM"),
        "2021-12-31",
        "2022-01-07",
        5,
    ),
)


@pytest.mark.parametrize("tickers, start, end, len_", ALL_HISTORY_CASES)
def test_all_history_date(tickers, start, end, len_):
    """Проверка корректности учета торговых дат для ограниченного набора тикеров.

    Только иностранные акции торговались 2022-01-07.
    """
    dates = listing.all_history_date(tickers, start=start, end=end)
    assert isinstance(dates, pd.Index)
    assert len(dates) == len_


def test_securities_with_reg_number():
    """Проверка типа, количества и присутствия ДР."""
    securities = listing.securities()
    assert isinstance(securities, pd.Index)
    assert securities.size >= 263
    assert "AGRO" in securities
    assert "YNDX" in securities
    assert "BANEP" in securities


TYPE_CASES = (
    ("AKRN", 0),
    ("FIVE", 0),
    ("VEON-RX", 0),
    ("RTKMP", 1),
    ("AMD-RM", 2),
    ("FXDE", 3),
)


@pytest.mark.parametrize("ticker, type_", TYPE_CASES)
def test_ticker_types(ticker, type_):
    """Проверка типа ценной бумаги."""
    ticker_types = listing.ticker_types()

    assert isinstance(ticker_types, pd.Series)
    assert len(ticker_types) > 368
    assert ticker_types[ticker] == type_


LOT_CASES = (
    (("AKRN", "MOEX"), (1, 10)),
    (("MTSS", "MOEX", "MRSB"), (10, 10, 10000)),
    (("SNGSP", "TTLK", "PMSBP", "RTKM", "SIBN"), (100, 1000, 10, 10, 10)),
)


@pytest.mark.parametrize("ticker, lots", LOT_CASES)
def test_lot_size(ticker, lots):
    """Проверка типа данных и размера лотов."""
    lots_data = listing.lot_size(ticker)

    assert isinstance(lots_data, pd.Series)
    assert len(lots_data) == len(ticker)
    assert tuple(lots_data.values) == lots
