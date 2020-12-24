"""Тесты обрезки данных по дивидендам."""
import pandas as pd
import pytest

from poptimizer.data.app import bootstrap
from poptimizer.data.views.crop import div

DIV_CASES = (
    ("SBER", ("2015-06-15", 0.45)),
    ("SBERP", ("2016-06-14", 1.97)),
    ("CHMF", ("2018-06-19", 27.72 + 38.32)),
    ("CHMF", ("2018-06-19", 27.72 + 38.32)),
    ("TRNFP", ("2020-10-20", 11612.2)),
)


@pytest.mark.parametrize("ticker, div_data", DIV_CASES)
def test_conomy(ticker, div_data):
    """Проверка, что первые дивиденды после даты обрезки."""
    df = div.conomy(ticker)

    assert isinstance(df, pd.DataFrame)
    assert df.index.is_monotonic_increasing
    assert df.index[0] >= bootstrap.get_start_date()
    assert df.columns.tolist() == [ticker]

    date, div_value = div_data
    assert df.loc[date, ticker] == div_value


@pytest.mark.parametrize("ticker, div_data", DIV_CASES)
def test_bcs(ticker, div_data):
    """Проверка, что первые дивиденды после даты обрезки."""
    df = div.bcs(ticker)

    assert isinstance(df, pd.DataFrame)
    assert df.index.is_monotonic_increasing
    assert df.index[0] >= bootstrap.get_start_date()
    assert df.columns.tolist() == [ticker]

    date, div_value = div_data
    assert df.loc[date, ticker] == div_value


@pytest.mark.parametrize("ticker, div_data", DIV_CASES)
def test_dohod(ticker, div_data):
    """Проверка, что первые дивиденды после даты обрезки."""
    df = div.dohod(ticker)

    assert isinstance(df, pd.DataFrame)
    assert df.index.is_monotonic_increasing
    assert df.index[0] >= bootstrap.get_start_date()
    assert df.columns.tolist() == [ticker]

    date, div_value = div_data
    assert df.loc[date, ticker] == div_value


@pytest.mark.parametrize("ticker, div_data", DIV_CASES)
def test_dividends(ticker, div_data):
    """Проверка, что первые дивиденды после даты обрезки."""
    df = div.dividends(ticker)

    assert isinstance(df, pd.DataFrame)
    assert df.index.is_monotonic_increasing

    assert df.index[0] >= bootstrap.get_start_date()
    assert df.columns.tolist() == [ticker]

    date, div_value = div_data
    assert df.loc[date, ticker] == div_value


DIVIDENDS_CASES = (
    ("2018-06-19", "CHMF", 38.32 + 27.72),
    ("2017-12-05", "CHMF", 35.61),
    ("2018-07-17", "GMKN", 607.98),
    ("2017-10-19", "GMKN", 224.2),
    ("2018-06-19", "GMKN", 0),
    ("2018-07-17", "CHMF", 0),
)


@pytest.mark.parametrize("date, ticker, div_value", DIVIDENDS_CASES)
def test_dividends_all(date, ticker, div_value):
    """Тесты на размер результата и для выборочных значений и заполнение пропусков."""
    df = div.dividends_all(("CHMF", "GMKN"))

    assert len(df) > 30
    assert list(df.columns) == ["CHMF", "GMKN"]

    assert df.index[0] == pd.Timestamp("2015-05-25")
    assert df.index[-1] >= pd.Timestamp("2020-09-08")

    div_after_tax = div_value * bootstrap.get_after_tax_rate()
    assert df.loc[date, ticker] == pytest.approx(div_after_tax)
