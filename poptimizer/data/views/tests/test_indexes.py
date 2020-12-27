"""Тесты различных индексов."""
import pandas as pd
import pytest

from poptimizer.data.app import bootstrap
from poptimizer.data.views import indexes
from poptimizer.shared import col

CPI_CASES = (
    ("2020-09-30", 0.9993),
    ("2018-11-30", 1.005),
    ("2018-06-30", 1.0049),
    ("2017-07-31", 1.0007),
    ("2017-08-31", 0.9946),
    ("2015-01-31", 1.0385),
)


@pytest.mark.parametrize("date, cpi", CPI_CASES)
def test_cpi(date, cpi):
    """Проверка, что первые и последние данные обрезаны корректно и значения совпадают."""
    df = indexes.cpi(pd.Timestamp("2020-10-10"))

    assert isinstance(df, pd.Series)
    assert df.index.is_monotonic_increasing

    assert df.index[0] >= bootstrap.START_DATE
    assert df.index[-1] == pd.Timestamp("2020-09-30")

    assert df.loc[date] == pytest.approx(cpi)


INDEX_CASES = (
    ("2018-03-02", 3273.16),
    ("2018-03-16", 3281.58),
    ("2018-12-24", 3492.91),
    ("2020-10-01", 4799.92),
)


@pytest.mark.parametrize("date, index", INDEX_CASES)
def test_mcftrr(date, index):
    """Проверка, что первые данные обрезаны."""
    df = indexes.mcftrr(pd.Timestamp("2020-10-09"))

    assert isinstance(df, pd.Series)
    assert df.index.is_monotonic_increasing and df.name == col.CLOSE

    assert df.index[0] >= bootstrap.START_DATE
    assert df.index[-1] == pd.Timestamp("2020-10-09")

    assert df.loc[date] == pytest.approx(index)


RVI_CASES = (
    ("2015-01-05", 74.3),
    ("2020-03-18", 118.24),
    ("2020-10-16", 27.35),
)


@pytest.mark.parametrize("date, index", RVI_CASES)
def test_rvi(date, index):
    """Проверка, что первые данные обрезаны."""
    df = indexes.rvi(pd.Timestamp("2020-10-16"))

    assert isinstance(df, pd.Series)
    assert df.index.is_monotonic_increasing and df.name == col.CLOSE

    assert df.index[0] >= bootstrap.START_DATE
    assert df.index[-1] == pd.Timestamp("2020-10-16")

    assert df.loc[date] == pytest.approx(index)
