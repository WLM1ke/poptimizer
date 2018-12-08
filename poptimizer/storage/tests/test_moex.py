import pandas as pd
import pytest

from poptimizer.storage import client, moex, manager
from poptimizer.storage.utils import (
    REG_NUMBER,
    LOT_SIZE,
    TICKER,
    CLOSE,
    VALUE,
    MOEX_TZ,
    DATE,
)


@pytest.fixture(autouse=True)
@pytest.mark.asyncio
async def create_client():
    async with client.Client():
        yield


@pytest.mark.asyncio
async def fake_update_timestamp(_):
    return pd.Timestamp.now(MOEX_TZ) + pd.DateOffset(days=1)


@pytest.mark.asyncio
async def test_securities_info(monkeypatch):
    monkeypatch.setattr(manager.utils, "update_timestamp", fake_update_timestamp)

    df = await moex.Securities().get()
    assert len(df.index) > 200
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


# noinspection PyProtectedMember
@pytest.mark.asyncio
async def test_quotes_find_aliases():
    assert set(await moex.Quotes._find_aliases("UPRO")) == {"UPRO", "EONR", "OGK4"}


# noinspection PyTypeChecker
@pytest.mark.asyncio
async def test_quotes_fake_create(monkeypatch):
    monkeypatch.setattr(manager.utils, "update_timestamp", fake_update_timestamp)

    db = moex.Quotes("MSTT")
    monkeypatch.setattr(db, "_data", {"MSTT": None})
    df = await db.get()

    assert isinstance(df, pd.DataFrame)
    assert df.shape[0] > 1000
    assert df.index[0] == pd.to_datetime("2010-11-03")
    assert df.loc["2013-03-27", CLOSE] == pytest.approx(136.3)
    assert df.loc["2014-06-09", CLOSE] == pytest.approx(110.48)
    assert df.loc["2018-09-07", CLOSE] == pytest.approx(92.0)
    assert df.loc["2018-03-09", CLOSE] == 148.8
    assert df.loc["2018-03-09", VALUE] == 439722


# noinspection PyTypeChecker
@pytest.mark.asyncio
async def test_quotes_fake_update(monkeypatch):
    monkeypatch.setattr(manager.utils, "update_timestamp", fake_update_timestamp)

    df = await moex.Quotes("AKRN").get()
    assert isinstance(df, pd.DataFrame)
    assert len(df) > 3000

    assert df.index.name == DATE
    assert all(df.columns == [CLOSE, VALUE])

    assert df.index[0] == pd.Timestamp("2006-10-20")
    assert df[CLOSE].iloc[0] == pytest.approx(834.93)
    assert df[VALUE].iloc[0] == pytest.approx(13863.93)
    assert df.index[-1] >= pd.Timestamp("2018-12-07")


# noinspection PyTypeChecker
@pytest.mark.asyncio
async def test_quotes_akrn():
    df = await moex.Quotes("AKRN").get()

    assert isinstance(df, pd.DataFrame)
    assert len(df) > 3000
    assert df.index[0] == pd.Timestamp("2006-10-20")
    assert df[CLOSE].iloc[0] == pytest.approx(834.93)
    assert df[VALUE].iloc[0] == pytest.approx(13863.93)
    assert df.index[-1] >= pd.Timestamp("2018-12-07")
    assert df.loc["2014-06-10", VALUE] == pytest.approx(20317035.8)
    assert df.loc["2018-09-10", CLOSE] == pytest.approx(4528)


# noinspection PyTypeChecker
@pytest.mark.asyncio
async def test_quotes_moex():
    df = await moex.Quotes("MOEX").get()

    assert df.shape[0] > 1300
    assert df.index[0] == pd.Timestamp("2013-02-15")
    assert df.loc["2018-03-05", CLOSE] == pytest.approx(117)
    assert df.loc["2018-03-05", VALUE] == pytest.approx(533142058.2)


# noinspection PyTypeChecker
@pytest.mark.asyncio
async def test_quotes_upro():
    df = await moex.Quotes("UPRO").get()

    assert df.shape[0] > 2500
    assert df.index[0] == pd.to_datetime("2007-05-24")
    assert df.iloc[1, 0] == pytest.approx(2.65)
    assert df.iloc[2, 1] == pytest.approx(997822.7)
    assert df.loc["2018-09-07", CLOSE] == pytest.approx(2.633)
    assert df.loc["2018-09-10", VALUE] == pytest.approx(24565585)


# noinspection PyTypeChecker
@pytest.mark.asyncio
async def test_quotes_banep():
    df = await moex.Quotes("BANEP").get()

    assert df.index[0] == pd.to_datetime("2011-11-18")
    assert df.loc["2014-06-10", CLOSE] == pytest.approx(1833.0)
    assert df.loc["2014-06-11", VALUE] == pytest.approx(42394025.2)
    assert df.shape[0] > 1000
    assert df.loc["2018-09-07", CLOSE] == pytest.approx(1721.5)
    assert df.loc["2018-09-10", VALUE] == pytest.approx(60677908)


# noinspection PyTypeChecker
@pytest.mark.asyncio
async def test_quotes_sberp():
    df = await moex.Quotes("SBERP").get()

    assert df.shape[0] > 1000
    assert df.index[0] == pd.to_datetime("2007-07-20")
    assert df.loc["2013-03-26", CLOSE] == pytest.approx(72.20)
    assert df.loc["2018-09-10", CLOSE] == pytest.approx(148.36)


# noinspection PyTypeChecker
@pytest.mark.asyncio
async def test_quotes_gmkn():
    df = await moex.Quotes("GMKN").get()

    assert df.shape[0] > 1000
    assert df.index[0] == pd.to_datetime("2006-12-26")
    assert df.loc["2014-06-09", VALUE] == pytest.approx(1496171686)
    assert df.loc["2018-09-07", CLOSE] == pytest.approx(11200)


# noinspection PyTypeChecker
@pytest.mark.asyncio
async def test_quotes_mstt():
    df = await moex.Quotes("MSTT").get()

    assert df.shape[0] > 1000
    assert df.index[0] == pd.to_datetime("2010-11-03")
    assert df.loc["2013-03-27", CLOSE] == pytest.approx(136.3)
    assert df.loc["2014-06-09", CLOSE] == pytest.approx(110.48)
    assert df.loc["2018-09-07", CLOSE] == pytest.approx(92.0)
    assert df.loc["2018-03-09", CLOSE] == 148.8
    assert df.loc["2018-03-09", VALUE] == 439722


# noinspection PyTypeChecker
@pytest.mark.asyncio
async def test_quotes_kbtk():
    df = await moex.Quotes("KBTK").get()

    assert "2018-03-09" not in df.index
    assert df.loc["2018-03-12", CLOSE] == pytest.approx(145)
    assert df.loc["2018-04-04", VALUE] == pytest.approx(11095465)


# noinspection PyTypeChecker
@pytest.mark.asyncio
async def test_quotes_rtkmp():
    df = await moex.Quotes("RTKMP").get()

    assert df.loc["2018-03-13", VALUE] == pytest.approx(24716781)
    assert df.loc["2018-03-13", CLOSE] == pytest.approx(62)
    assert df.loc["2018-04-11", CLOSE] == pytest.approx(60.3)


# noinspection PyTypeChecker
@pytest.mark.asyncio
async def test_quotes_lsngp():
    df = await moex.Quotes("LSNGP").get()

    assert df.index[0] == pd.Timestamp("2005-08-03")
    assert df.loc["2014-06-09", CLOSE] == pytest.approx(14.7)
    assert df.loc["2014-10-28", VALUE] == 1132835
    assert df.loc["2018-09-07", CLOSE] == pytest.approx(86.5)
    assert df.loc["2018-05-31", VALUE] == 24798580
    assert df.loc["2018-12-07", CLOSE] == pytest.approx(95.82)


# noinspection PyTypeChecker
@pytest.mark.asyncio
async def test_quotes_lsrg():
    df = await moex.Quotes("LSRG").get()

    assert df.index[0] == pd.Timestamp("2007-11-30")
    assert df.loc["2018-08-07", CLOSE] == pytest.approx(777)
    assert df.loc["2018-08-10", VALUE] == pytest.approx(8626464.5)
    assert df.loc["2018-09-06", CLOSE] == pytest.approx(660)
    assert df.loc["2018-08-28", VALUE] == 34666629.5
