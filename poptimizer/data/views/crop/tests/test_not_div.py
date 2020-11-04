"""Тесты end-to-end для обрезки для различных представлений данных."""
import datetime

import pandas as pd
import pytest

from poptimizer.data.config import bootstrap
from poptimizer.data_di.shared import col
from poptimizer.data.views.crop import not_div

CPI_CASES = (
    ("2018-11-30", 1.005),
    ("2018-06-30", 1.0049),
    ("2017-07-31", 1.0007),
    ("2017-08-31", 0.9946),
    ("2015-01-31", 1.0385),
)


@pytest.mark.parametrize("date, cpi", CPI_CASES)
def test_cpi(date, cpi):
    """Проверка, что первые данные обрезаны и их нужное количество."""
    df = not_div.cpi()

    assert isinstance(df, pd.Series)
    assert df.index.is_monotonic_increasing

    today = datetime.date.today()
    start = bootstrap.get_start_date()
    months = (today.year - start.year) * 12
    months += today.month - start.month

    assert months - 1 <= len(df) <= months
    assert df.index[0] >= bootstrap.get_start_date()
    assert df.loc[date] == pytest.approx(cpi)


INDEX_CASES = (
    ("2018-03-02", 3273.16),
    ("2018-03-16", 3281.58),
    ("2018-12-24", 3492.91),
    ("2020-10-01", 4799.92),
)


@pytest.mark.parametrize("date, index", INDEX_CASES)
def test_index(date, index):
    """Проверка, что первые данные обрезаны."""
    df = not_div.index()

    assert isinstance(df, pd.Series)
    assert df.index.is_monotonic_increasing
    assert df.index[0] >= bootstrap.get_start_date()
    assert df.name == col.CLOSE
    assert df.loc[date] == pytest.approx(index)


QUOTES_CASES = (
    (("AKRN",), 0, ("2015-06-10", col.TURNOVER), 7227902),
    (("AKRN",), 0, ("2018-09-10", col.CLOSE), 4528),
    (("MOEX", "UPRO"), 0, ("2018-03-05", col.CLOSE), 117),
    (("MOEX", "UPRO"), 1, ("2018-09-07", col.CLOSE), 2.633),
    (("MOEX", "UPRO"), 1, ("2018-09-10", col.TURNOVER), 24565585),
)


@pytest.mark.parametrize("tickers, pos, loc, quote", QUOTES_CASES)
def test_quotes(tickers, pos, loc, quote):
    """Проверка, что первые данные обрезаны."""
    dfs = not_div.quotes(tickers)

    assert len(dfs) == len(tickers)
    df = dfs[pos]

    assert df.index.is_monotonic_increasing
    assert df.index[0] >= bootstrap.get_start_date()
    columns = [col.OPEN, col.CLOSE, col.HIGH, col.LOW, col.TURNOVER]
    assert df.columns.tolist() == columns
    assert df.loc[loc] == pytest.approx(quote)
