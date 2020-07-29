import pandas as pd
import pytest

from poptimizer.config import POptimizerError
from poptimizer.store import moex
from poptimizer.store.moex import SECURITIES, INDEX, LISTING
from poptimizer.store.mongo import MONGO_CLIENT
from poptimizer.store.utils import REG_NUMBER, LOT_SIZE, TICKER, CLOSE, TURNOVER, DATE


@pytest.fixture(scope="module", autouse=True)
def manager_in_clean_test_db():
    MONGO_CLIENT.drop_database("test")
    yield
    MONGO_CLIENT.drop_database("test")


def test_securities():
    mng = moex.Securities(db="test")
    df = mng[SECURITIES]
    assert len(df.index) > 250
    assert all(df.columns == [REG_NUMBER, LOT_SIZE])
    assert df.index.name == TICKER

    assert df.index[0] == "ABRD"
    assert df[REG_NUMBER].iat[0] == "1-02-12500-A"
    assert df[LOT_SIZE].iat[0] == 10

    assert df[REG_NUMBER].iat[-1] == "1-01-00169-D"
    assert df[LOT_SIZE].iat[-1] == 1000
    assert df.index[-1] == "ZVEZ"

    assert df.loc["GAZP", REG_NUMBER] == "1-02-00028-A"
    assert df.loc["MOEX", REG_NUMBER] == "1-05-08443-H"
    assert df.loc["MRSB", REG_NUMBER] == "1-01-55055-E"
    assert df.loc["AKRN", LOT_SIZE] == 1
    assert df.loc["KBTK", LOT_SIZE] == 10
    assert df.loc["MOEX", LOT_SIZE] == 10
    assert df.loc["MRSB", LOT_SIZE] == 10000
    assert df.loc["MTSS", LOT_SIZE] == 10
    assert df.loc["SNGSP", LOT_SIZE] == 100
    assert df.loc["TTLK", LOT_SIZE] == 10000


def test_securities_wrong_id():
    mng = moex.Securities(db="test")
    with pytest.raises(POptimizerError) as error:
        # noinspection PyStatementEffect
        mng["QQQ"]
    assert "Отсутствуют данные test.misc.QQQ" == str(error.value)


def test_securities_listing():
    mng = moex.SecuritiesListing(db="test")
    df = mng[LISTING]
    assert len(df) > 2000
    assert df.loc["POLY", REG_NUMBER] is None
    assert df.loc["POLY", DATE] is None
    assert df.loc["IRAO", REG_NUMBER] == "1-04-33498-E"
    assert pd.Timestamp(df.loc["IRAO", DATE]) == pd.Timestamp("2014-12-23")


def test_securities_listing_wrong_id():
    mng = moex.SecuritiesListing(db="test")
    with pytest.raises(POptimizerError) as error:
        # noinspection PyStatementEffect
        mng["PPP"]
    assert "Отсутствуют данные test.misc.PPP" == str(error.value)


def test_index():
    mng = moex.Index(db="test")
    df = mng[INDEX]
    assert isinstance(df, pd.DataFrame)
    assert len(df) > 3750
    assert df.columns == [CLOSE]
    assert df.index[0] == pd.Timestamp("2003-02-26")
    assert df.loc["2003-02-26", CLOSE] == 335.67
    assert df.loc["2018-03-02", CLOSE] == 3273.16
    assert df.loc["2018-12-24", CLOSE] == 3492.91


def test_index_wrong_id():
    mng = moex.Index(db="test")
    with pytest.raises(POptimizerError) as error:
        # noinspection PyStatementEffect
        mng["QQQ"]
    assert "Отсутствуют данные test.misc.QQQ" == str(error.value)


def test_index_download_update():
    mng = moex.Index(db="test")
    # noinspection PyProtectedMember
    data = mng._download(INDEX, pd.Timestamp("2019-09-13"))
    assert isinstance(data, list)
    assert len(data) >= 1
    assert data[0] == {"CLOSE": 4400.91, "DATE": pd.Timestamp("2019-09-13")}


def test_quotes_create():
    mng = moex.Quotes(db="test")
    df = mng["MSTT"]

    assert isinstance(df, pd.DataFrame)
    assert df.shape[0] > 1000
    assert df.index[0] == pd.to_datetime("2010-11-03")
    assert df.loc["2013-03-27", CLOSE] == pytest.approx(136.3)
    assert df.loc["2014-06-09", CLOSE] == pytest.approx(110.48)
    assert df.loc["2018-09-07", CLOSE] == pytest.approx(92.0)
    assert df.loc["2018-03-09", CLOSE] == 148.8
    assert df.loc["2018-03-09", TURNOVER] == 439722


def test_quotes_download_update():
    mng = moex.Quotes(db="test")
    # noinspection PyProtectedMember
    data = mng._download("MSTT", last_index=pd.Timestamp("2019-09-13"))
    assert len(data)
    assert data[0][CLOSE] == 88.7
    assert data[0][TURNOVER] == 1106728


def test_quotes_late_reg_number():
    """Под тикером IRAO обращалось две бумаги с разными регистрационными номерами.

    Это вызывало скачек котировок в сто раз.
    """
    mng = moex.Quotes(db="test")
    df = mng["IRAO"]

    assert isinstance(df, pd.DataFrame)
    assert df.shape[0] > 1270
    assert df.index[0] == pd.to_datetime("2015-01-20")
    assert df.loc["2015-01-20", CLOSE] == pytest.approx(0.7641)
    assert df.loc["2015-01-20", TURNOVER] == pytest.approx(55127750.3)
    assert df.loc["2020-02-03", CLOSE] == pytest.approx(5.8285)
    assert df.loc["2020-02-03", TURNOVER] == pytest.approx(1156252597.5)


def test_quotes_find_aliases():
    mng = moex.Quotes(db="test")
    # noinspection PyProtectedMember
    tickers, date = mng._find_aliases("UPRO")
    assert set(tickers) == {"UPRO", "EONR", "OGK4"}
    assert date == pd.Timestamp("2007-04-19")


def test_quotes_no_data():
    """Некоторые бумаги не имеют котировок."""
    mng = moex.Quotes(db="test")
    for ticker in ("KSGR", "KMTZ", "TRFM"):
        df = mng[ticker]
        assert isinstance(df, pd.DataFrame)
        assert df.empty


def test_not_unique():
    """Некоторые бумаги со старой историей торговались одновременно под несколькими тикерами."""
    mng = moex.Quotes(db="test")
    for ticker in ("PRMB", "OGKB"):
        df = mng[ticker]
        assert isinstance(df, pd.DataFrame)
        assert df.index.is_unique
        assert df.index.is_monotonic_increasing


def test_no_reg_number():
    mng = moex.Quotes(db="test")
    with pytest.raises(POptimizerError) as error:
        # noinspection PyStatementEffect
        mng["YNDX"]
    assert "YNDX - акция без регистрационного номера" == str(error.value)
