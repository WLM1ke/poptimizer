import pandas as pd
import pytest

from poptimizer.data import moex
from poptimizer.store import CLOSE, TURNOVER


def test_securities_with_reg_number():
    result = moex.securities_with_reg_number()
    assert isinstance(result, pd.Index)
    assert result.size >= 249
    assert "AGRO" not in result
    assert "YNDX" not in result
    assert "BANEP" in result


def test_lot_size_all():
    df = moex.lot_size()

    assert isinstance(df, pd.Series)
    assert len(df) > 200

    assert df.index[0] == "ABRD"
    assert df.iat[0] == 10

    assert df.iat[-1] == 1000
    assert df.index[-1] == "ZVEZ"

    assert df["AKRN"] == 1
    assert df["KBTK"] == 10
    assert df["MOEX"] == 10
    assert df["MRSB"] == 10000
    assert df["MTSS"] == 10
    assert df["SNGSP"] == 100
    assert df["TTLK"] == 10000
    assert df["PMSBP"] == 10


def test_lot_size_some():
    df = moex.lot_size(("RTKM", "SIBN", "MRSB"))

    assert isinstance(df, pd.Series)
    assert len(df) == 3

    assert df["RTKM"] == 10
    assert df["SIBN"] == 10
    assert df["MRSB"] == 10000


def test_index():
    df = moex.index(pd.Timestamp("2018-12-24"))
    assert isinstance(df, pd.Series)
    assert len(df) > 3750
    assert df.index[0] == pd.Timestamp("2003-02-26")
    assert df.index[-1] == pd.Timestamp("2018-12-24")
    assert df["2003-02-26"] == 335.67
    assert df["2018-03-02"] == 3273.16
    assert df["2018-03-16"] == 3281.58
    assert df["2018-12-24"] == 3492.91


def test_no_data():
    """Некоторые бумаги не имеют котировок.

    Дополнительная проверка, что эта ситуация обрабатывается без ошибок.
    """
    quotes_list = moex.quotes(("KSGR", "KMTZ", "TRFM"))
    for df in quotes_list:
        assert isinstance(df, pd.DataFrame)
        assert df.empty


def test_multi_tickers():
    """Некоторые бумаги со старой историей торговались одновременно под несколькими тикерами.

    Дополнительная проверка, что у данных уникальный возрастающий индекс.
    """
    quotes_list = moex.quotes(("PRMB", "OGKB"))
    for df in quotes_list:
        assert isinstance(df, pd.DataFrame)
        assert df.index.is_unique
        assert df.index.is_monotonic_increasing


def test_prices():
    df = moex.prices(("AKRN", "GMKN", "GTSS", "KBTK"), pd.Timestamp("2018-12-06"))
    assert isinstance(df, pd.DataFrame)
    assert len(df) > 3000
    assert df.shape[1] == 4
    assert df.index[-1] == pd.Timestamp("2018-12-06")

    assert df.loc["2006-10-20", "AKRN"] == pytest.approx(834.93)
    assert df.loc["2018-09-10", "AKRN"] == pytest.approx(4528)

    assert df.loc["2018-09-07", "GMKN"] == pytest.approx(11200)
    assert df.loc["2018-12-06", "GMKN"] == pytest.approx(12699)

    assert df.loc["2018-03-12", "KBTK"] == pytest.approx(145)
    assert df.loc["2010-05-24", "KBTK"] == pytest.approx(180)

    df = df["GTSS"]
    df.dropna(axis=0, inplace=True)
    assert df.empty


def test_zero_prices():
    df = moex.prices(("AKRN", "KAZTP"), pd.Timestamp("2018-12-14"))
    assert df.loc["2012-03-12", "KAZTP"] == pytest.approx(46.011)
    assert df.loc["2012-03-15", "KAZTP"] == pytest.approx(47.101)


def test_turnovers():
    df = moex.turnovers(("PMSBP", "GTSS", "RTKM"), pd.Timestamp("2018-12-05"))
    assert isinstance(df, pd.DataFrame)
    assert len(df) > 3000
    assert df.shape[1] == 3
    assert df.index[-1] == pd.Timestamp("2018-12-05")

    assert df.loc["2003-10-08", "PMSBP"] == pytest.approx(0)
    assert df.loc["2018-10-10", "PMSBP"] == pytest.approx(148056)

    assert df.loc["2003-10-09", "RTKM"] == pytest.approx(1485834851.93)
    assert df.loc["2018-12-05", "RTKM"] == pytest.approx(117397440.3)

    assert (df["GTSS"] == 0).all()


def test_quotes_akrn():
    df = moex.quotes(("AKRN",))[0]

    assert isinstance(df, pd.DataFrame)
    assert len(df) > 3000
    assert df.index[0] == pd.Timestamp("2006-10-20")
    assert df[CLOSE].iloc[0] == pytest.approx(834.93)
    assert df[TURNOVER].iloc[0] == pytest.approx(13863.93)
    assert df.index[-1] >= pd.Timestamp("2018-12-07")
    assert df.loc["2014-06-10", TURNOVER] == pytest.approx(20317035.8)
    assert df.loc["2018-09-10", CLOSE] == pytest.approx(4528)


def test_quotes_moex():
    df = moex.quotes(("MOEX",))[0]

    assert df.shape[0] > 1300
    assert df.index[0] == pd.Timestamp("2013-02-15")
    assert df.loc["2018-03-05", CLOSE] == pytest.approx(117)
    assert df.loc["2018-03-05", TURNOVER] == pytest.approx(533142058.2)


def test_quotes_upro():
    df = moex.quotes(("UPRO",))[0]

    assert df.shape[0] > 2500
    assert df.index[0] == pd.to_datetime("2007-05-24")
    assert df.loc["2007-05-25", CLOSE] == pytest.approx(2.65)
    assert df.loc["2007-05-28", TURNOVER] == pytest.approx(997822.7)
    assert df.loc["2018-09-07", CLOSE] == pytest.approx(2.633)
    assert df.loc["2018-09-10", TURNOVER] == pytest.approx(24565585)


def test_quotes_banep():
    df = moex.quotes(("BANEP",))[0]

    assert df.index[0] == pd.to_datetime("2011-11-18")
    assert df.loc["2014-06-10", CLOSE] == pytest.approx(1833.0)
    assert df.loc["2014-06-11", TURNOVER] == pytest.approx(42394025.2)
    assert df.shape[0] > 1000
    assert df.loc["2018-09-07", CLOSE] == pytest.approx(1721.5)
    assert df.loc["2018-09-10", TURNOVER] == pytest.approx(60677908)


def test_quotes_sberp():
    df = moex.quotes(("SBERP",))[0]

    assert df.shape[0] > 1000
    assert df.index[0] == pd.to_datetime("2007-07-20")
    assert df.loc["2013-03-26", CLOSE] == pytest.approx(72.20)
    assert df.loc["2018-09-10", CLOSE] == pytest.approx(148.36)


def test_quotes_gmkn():
    df = moex.quotes(("GMKN",))[0]

    assert df.shape[0] > 1000
    assert df.index[0] == pd.to_datetime("2006-12-26")
    assert df.loc["2014-06-09", TURNOVER] == pytest.approx(1496171686)
    assert df.loc["2018-09-07", CLOSE] == pytest.approx(11200)


def test_quotes_mstt():
    df = moex.quotes(("MSTT",))[0]

    assert df.shape[0] > 1000
    assert df.index[0] == pd.to_datetime("2010-11-03")
    assert df.loc["2013-03-27", CLOSE] == pytest.approx(136.3)
    assert df.loc["2014-06-09", CLOSE] == pytest.approx(110.48)
    assert df.loc["2018-09-07", CLOSE] == pytest.approx(92.0)
    assert df.loc["2018-03-09", CLOSE] == 148.8
    assert df.loc["2018-03-09", TURNOVER] == 439722


def test_quotes_kbtk():
    df = moex.quotes(("KBTK",))[0]

    assert "2018-03-09" not in df.index
    assert df.loc["2018-03-12", CLOSE] == pytest.approx(145)
    assert df.loc["2018-04-04", TURNOVER] == pytest.approx(11095465)


def test_quotes_rtkmp():
    df = moex.quotes(("RTKMP",))[0]

    assert df.loc["2018-03-13", TURNOVER] == pytest.approx(24716781)
    assert df.loc["2018-03-13", CLOSE] == pytest.approx(62)
    assert df.loc["2018-04-11", CLOSE] == pytest.approx(60.3)


def test_quotes_lsngp():
    df = moex.quotes(("LSNGP",))[0]

    assert df.index[0] == pd.Timestamp("2005-08-03")
    assert df.loc["2014-06-09", CLOSE] == pytest.approx(14.7)
    assert df.loc["2014-10-28", TURNOVER] == 1132835
    assert df.loc["2018-09-07", CLOSE] == pytest.approx(86.5)
    assert df.loc["2018-05-31", TURNOVER] == 24798580
    assert df.loc["2018-12-07", CLOSE] == pytest.approx(95.82)


def test_quotes_lsrg():
    df = moex.quotes(("LSRG",))[0]

    assert df.index[0] == pd.Timestamp("2007-11-30")
    assert df.loc["2018-08-07", CLOSE] == pytest.approx(777)
    assert df.loc["2018-08-10", TURNOVER] == pytest.approx(8626464.5)
    assert df.loc["2018-09-06", CLOSE] == pytest.approx(660)
    assert df.loc["2018-08-28", TURNOVER] == 34666629.5
