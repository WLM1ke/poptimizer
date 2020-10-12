"""Тесты end-to-end для обрезки для различных представлений данных."""
import datetime

import pandas as pd
import pytest

from poptimizer.data.config import bootstrap
from poptimizer.data.ports import col
from poptimizer.data.views import crop

DIV_CASES = (
    ("SBER", ("2015-06-15", 0.45)),
    ("SBERP", ("2016-06-14", 1.97)),
    ("CHMF", ("2018-06-19", 27.72 + 38.32)),
)


@pytest.mark.parametrize("ticker, div_data", DIV_CASES)
def test_conomy(ticker, div_data):
    """Проверка, что первые дивиденды после даты обрезки."""
    df = crop.conomy(ticker)

    assert isinstance(df, pd.DataFrame)
    assert df.index.is_monotonic_increasing
    assert df.index[0] >= bootstrap.get_start_date()
    assert df.columns.tolist() == [ticker]

    date, div = div_data
    assert df.loc[date, ticker] == div


@pytest.mark.parametrize("ticker, div_data", DIV_CASES)
def test_dohod(ticker, div_data):
    """Проверка, что первые дивиденды после даты обрезки."""
    df = crop.dohod(ticker)

    assert isinstance(df, pd.DataFrame)
    assert df.index.is_monotonic_increasing
    assert df.index[0] >= bootstrap.get_start_date()
    assert df.columns.tolist() == [ticker]

    date, div = div_data
    assert df.loc[date, ticker] == div


@pytest.mark.parametrize("ticker, div_data", DIV_CASES)
def test_dividends(ticker, div_data):
    """Проверка, что первые дивиденды после даты обрезки."""
    df = crop.dividends(ticker)

    assert isinstance(df, pd.DataFrame)
    assert df.index.is_monotonic_increasing

    assert df.index[0] >= bootstrap.get_start_date()
    assert df.columns.tolist() == [ticker]

    date, div = div_data
    assert df.loc[date, ticker] == div


DIVIDENDS_CASES = (
    ("2018-06-19", "CHMF", 38.32 + 27.72),
    ("2017-12-05", "CHMF", 35.61),
    ("2018-07-17", "GMKN", 607.98),
    ("2017-10-19", "GMKN", 224.2),
    ("2018-06-19", "GMKN", 0),
    ("2018-07-17", "CHMF", 0),
)


@pytest.mark.parametrize("date, ticker, div", DIVIDENDS_CASES)
def test_dividends_all(date, ticker, div):
    """Тесты на размер результата и для выборочных значений и заполнение пропусков."""
    df = crop.dividends_all(("CHMF", "GMKN"))

    assert len(df) > 30
    assert list(df.columns) == ["CHMF", "GMKN"]

    assert df.index[0] == pd.Timestamp("2015-05-25")
    assert df.index[-1] >= pd.Timestamp("2020-09-08")

    div_after_tax = div * bootstrap.get_after_tax_rate()
    assert df.loc[date, ticker] == pytest.approx(div_after_tax)


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
    df = crop.cpi()

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
    df = crop.index()

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
    dfs = crop.quotes(tickers)

    assert len(dfs) == len(tickers)
    df = dfs[pos]

    assert df.index.is_monotonic_increasing
    assert df.index[0] >= bootstrap.get_start_date()
    columns = [col.OPEN, col.CLOSE, col.HIGH, col.LOW, col.TURNOVER]
    assert df.columns.tolist() == columns
    assert df.loc[loc] == pytest.approx(quote)
