"""Тесты для данных по котировкам."""
import pandas as pd
import pytest

from poptimizer.data.app import bootstrap
from poptimizer.data.views import moex


def test_last_history_date():
    """Проверка на тип и относительную корректность результата."""
    date = moex.last_history_date()
    assert isinstance(date, pd.Timestamp)
    assert date < pd.Timestamp.now()
    assert date > pd.Timestamp.now() - pd.DateOffset(days=10)


def test_securities_with_reg_number():
    """Проверка типа, количества и присутствия ДР."""
    securities = moex.securities()
    assert isinstance(securities, pd.Index)
    assert securities.size >= 263
    assert "AGRO" in securities
    assert "YNDX" in securities
    assert "BANEP" in securities


LOT_CASES = (
    (("AKRN", "KBTK"), (1, 10)),
    (("MTSS", "MOEX", "MRSB"), (10, 10, 10000)),
    (("SNGSP", "TTLK", "PMSBP", "RTKM", "SIBN"), (100, 10000, 10, 10, 10)),
)


@pytest.mark.parametrize("ticker, lots", LOT_CASES)
def test_lot_size(ticker, lots):
    """Проверка типа данных и размера лотов."""
    lots_data = moex.lot_size(ticker)

    assert isinstance(lots_data, pd.Series)
    assert len(lots_data) == len(ticker)
    assert tuple(lots_data.values) == lots


PRICE_CASES = (
    ("2018-09-10", "AKRN", 4528),
    ("2018-09-07", "GMKN", 11200),
    ("2018-12-06", "GMKN", 12699),
    ("2018-03-12", "KBTK", 145),
    ("2020-09-18", "MSTT", 161),
    ("2020-10-09", "MSTT", 161),
)


@pytest.mark.parametrize("date, ticker, price", PRICE_CASES)
def test_prices(date, ticker, price):
    """Тесты на тип и размер результата и для выборочных значений и заполнение пропусков."""
    df = moex.prices(("AKRN", "GMKN", "KBTK", "MSTT"), pd.Timestamp("2020-10-09"))

    assert isinstance(df, pd.DataFrame)
    assert len(df) > 1452
    assert df.shape[1] == 4
    assert df.index[-1] == pd.Timestamp("2020-10-09")
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
    df = moex.turnovers(("PMSBP", "RTKM", "MSTT"), pd.Timestamp("2020-10-09"))

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
    index = moex.prices(("NLMK", "GMKN"), pd.Timestamp("2018-10-08")).index
    assert moex._t2_shift(pd.Timestamp(date), index) == pd.Timestamp(t2)


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
    rez = moex.div_and_prices(("KZOS", "LSRG", "LKOH", "SBERP"), pd.Timestamp("2020-10-09"))
    assert len(rez) == 2

    df = rez[df_n]
    assert list(df.columns) == ["KZOS", "LSRG", "LKOH", "SBERP"]
    assert df.index[0] == pd.Timestamp("2015-01-05")
    assert df.index[-1] == pd.Timestamp("2020-10-09")

    assert df.loc[date, ticker] == pytest.approx(chek)
