"""Тесты для отображения данных о котировках."""
import pandas as pd
import pytest

from poptimizer.data.app import bootstrap
from poptimizer.data.views import quotes
from poptimizer.shared import col

PRICE_CASES = (
    ("2018-09-10", "AKRN", 4528),
    ("2018-09-07", "GMKN", 11200),
    ("2018-12-06", "GMKN", 12699),
    ("2020-09-18", "MSTT", 161),
    ("2020-10-09", "MSTT", 161),
)


@pytest.mark.parametrize("date, ticker, price", PRICE_CASES)
def test_prices(date, ticker, price):
    """Тесты на тип и размер результата и для выборочных значений и заполнение пропусков."""
    df = quotes.prices(("AKRN", "GMKN", "MSTT"), pd.Timestamp("2020-10-09"))

    assert isinstance(df, pd.DataFrame)
    assert len(df) > 1452
    assert df.shape[1] == 3
    assert df.index[-1] == pd.Timestamp("2020-10-09")
    assert df.loc[date, ticker] == pytest.approx(price)


TYPED_PRICE_CASES = (
    ("2018-09-10", "AKRN", col.CLOSE, 4528),
    ("2021-02-11", "GMKN", col.OPEN, 25366),
    ("2021-02-12", "GMKN", col.LOW, 24878),
)


@pytest.mark.parametrize("date, ticker, price_type, price", TYPED_PRICE_CASES)
def test_prices_with_types(date, ticker, price_type, price):
    """Тесты на тип и размер результата и для выборочных значений и заполнение пропусков."""
    df = quotes.prices(("AKRN", "GMKN"), pd.Timestamp("2021-03-10"), price_type)

    assert isinstance(df, pd.DataFrame)
    assert len(df) > 1452
    assert df.shape[1] == 2
    assert df.index[-1] == pd.Timestamp("2021-03-10")
    assert df.loc[date, ticker] == pytest.approx(price)


TURNOVER_CASES = (
    ("2018-12-05", "RTKM", 117397440.3),
    ("2018-10-10", "PMSBP", 148056),
    ("2020-09-18", "MSTT", 10972179),
    ("2020-10-09", "MSTT", 0),
)


@pytest.mark.parametrize("date, ticker, turnover", TURNOVER_CASES)
def test_turnovers(date, ticker, turnover):
    """Тесты на тип и размер результата и для выборочных значений и заполнение пропусков."""
    df = quotes.turnovers(("PMSBP", "RTKM", "MSTT"), pd.Timestamp("2020-10-09"))

    assert isinstance(df, pd.DataFrame)
    assert len(df) > 1452
    assert df.shape[1] == 3
    assert df.index[-1] == pd.Timestamp("2020-10-09")
    assert df.loc[date, ticker] == pytest.approx(turnover)


T2_CASES = (
    ("2018-05-15", "2018-05-14"),
    ("2018-07-08", "2018-07-05"),
    ("2018-10-01", "2018-09-28"),
    ("2018-10-10", "2018-10-09"),
    ("2018-10-12", "2018-10-11"),
    ("2018-10-13", "2018-10-11"),
    ("2018-10-14", "2018-10-11"),
    ("2018-10-15", "2018-10-12"),
    ("2018-10-18", "2018-10-17"),
)


@pytest.mark.parametrize("date, t2", T2_CASES)
def test_t2_shift(date, t2):
    """Различные варианты сдвига около выходных."""
    index = quotes.prices(("NLMK", "GMKN"), pd.Timestamp("2018-10-08")).index
    assert quotes._t2_shift(pd.Timestamp(date), index) == pd.Timestamp(t2)


DIV_PRICE_CASES = (
    (0, "2020-10-01", "SBERP", 0),
    (0, "2020-10-02", "SBERP", 18.7 * bootstrap.AFTER_TAX),
    (0, "2020-10-05", "SBERP", 0),
    (1, "2019-09-13", "LSRG", 754),
    (1, "2019-09-12", "KZOS", 96.1),
    (1, "2019-09-11", "LKOH", 5540),
)


@pytest.mark.parametrize("df_n, date, ticker, chek", DIV_PRICE_CASES)
def test_div_and_prices(df_n, date, ticker, chek):
    """Проверка выборочных цен и дивидендов с учетом налогов и сдвига."""
    rez = quotes.div_and_prices(("KZOS", "LSRG", "LKOH", "SBERP"), pd.Timestamp("2020-10-09"))
    assert len(rez) == 2

    df = rez[df_n]
    assert list(df.columns) == ["KZOS", "LSRG", "LKOH", "SBERP"]
    assert df.index[0] == pd.Timestamp("2015-01-05")
    assert df.index[-1] == pd.Timestamp("2020-10-09")

    assert df.loc[date, ticker] == pytest.approx(chek)
