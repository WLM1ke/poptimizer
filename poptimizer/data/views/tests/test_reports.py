"""Тесты представлений данных для отчетов."""
import pandas as pd
import pytest

from poptimizer.data.config import bootstrap
from poptimizer.data.ports import col
from poptimizer.data.views import reports

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
    df = reports.cpi(pd.Timestamp("2020-10-10"))

    assert isinstance(df, pd.Series)
    assert df.index.is_monotonic_increasing

    assert df.index[0] >= bootstrap.get_start_date()
    assert df.index[-1] == pd.Timestamp("2020-09-30")

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
    df = reports.index(pd.Timestamp("2020-10-09"))

    assert isinstance(df, pd.Series)
    assert df.index.is_monotonic_increasing and df.name == col.CLOSE

    assert df.index[0] >= bootstrap.get_start_date()
    assert df.index[-1] == pd.Timestamp("2020-10-09")

    assert df.loc[date] == pytest.approx(index)
