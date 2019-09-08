import aiomoex
import pandas as pd
import pytest

from poptimizer.store import (
    client,
    moex,
    manager,
    lmbd,
    CLOSE,
    TURNOVER,
    TICKER,
    REG_NUMBER,
    LOT_SIZE,
)
from poptimizer.store.client import MAX_SIZE, MAX_DBS
from poptimizer.store.utils import MOEX_TZ


@pytest.fixture(scope="module", name="path")
def make_temp_dir(tmpdir_factory):
    temp_dir = tmpdir_factory.mktemp("store_moex")
    return temp_dir


@pytest.fixture
@pytest.mark.asyncio
async def fake_data_base(path):
    async with aiomoex.ISSClientSession() as session:
        with lmbd.DataStore(path, MAX_SIZE, MAX_DBS) as db:
            manager.AbstractManager.ISS_SESSION = session
            manager.AbstractManager.STORE = db
            yield


@pytest.mark.asyncio
async def fake_update_timestamp(_):
    return pd.Timestamp.now(MOEX_TZ) + pd.DateOffset(days=7)


@pytest.mark.usefixtures("fake_data_base")
@pytest.mark.asyncio
async def test_securities(monkeypatch):
    monkeypatch.setattr(manager.utils, "get_last_history_date", fake_update_timestamp)

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


@pytest.mark.usefixtures("fake_data_base")
@pytest.mark.asyncio
async def test_index_create():
    df = await moex.Index().get()
    assert isinstance(df, pd.Series)
    assert len(df) > 3750
    assert df.index[0] == pd.Timestamp("2003-02-26")
    assert df["2003-02-26"] == 335.67
    assert df["2018-03-02"] == 3273.16
    assert df["2018-12-24"] == 3492.91


@pytest.mark.usefixtures("fake_data_base")
@pytest.mark.asyncio
async def test_index_download_update():
    # noinspection PyProtectedMember
    df = await moex.Index()._download("MCFTRR")
    assert isinstance(df, pd.Series)
    assert len(df) == 1
    assert df.index[0] >= pd.Timestamp("2018-12-24")


@pytest.mark.usefixtures("fake_data_base")
@pytest.mark.asyncio
async def test_quotes_create():
    df = await moex.Quotes(("MSTT",)).get()

    assert isinstance(df, pd.DataFrame)
    assert df.shape[0] > 1000
    assert df.index[0] == pd.to_datetime("2010-11-03")
    assert df.loc["2013-03-27", CLOSE] == pytest.approx(136.3)
    assert df.loc["2014-06-09", CLOSE] == pytest.approx(110.48)
    assert df.loc["2018-09-07", CLOSE] == pytest.approx(92.0)
    assert df.loc["2018-03-09", CLOSE] == 148.8
    assert df.loc["2018-03-09", TURNOVER] == 439722


@pytest.mark.usefixtures("fake_data_base")
@pytest.mark.asyncio
async def test_quotes_start_of_download_update():
    mng = moex.Quotes(("MSTT",))
    await mng.get()
    # noinspection PyProtectedMember
    update = await mng._download_update("MSTT")
    assert update.index[0] >= pd.Timestamp("2018-12-10")


@pytest.mark.usefixtures("fake_data_base")
@pytest.mark.asyncio
async def test_quotes_fake_update(monkeypatch):
    monkeypatch.setattr(manager.utils, "get_last_history_date", fake_update_timestamp)

    df = await moex.Quotes(("MSTT",)).get()

    assert isinstance(df, pd.DataFrame)
    assert df.shape[0] > 1000
    assert df.index[0] == pd.to_datetime("2010-11-03")
    assert df.loc["2013-03-27", CLOSE] == pytest.approx(136.3)
    assert df.loc["2014-06-09", CLOSE] == pytest.approx(110.48)
    assert df.loc["2018-09-07", CLOSE] == pytest.approx(92.0)
    assert df.loc["2018-03-09", CLOSE] == 148.8
    assert df.loc["2018-03-09", TURNOVER] == 439722


@pytest.mark.usefixtures("fake_data_base")
@pytest.mark.asyncio
async def test_no_data():
    """Некоторые бумаги не имеют котировок."""
    mgr = moex.Quotes(("KSGR", "KMTZ", "TRFM"))
    for ticker in ("KSGR", "KMTZ", "TRFM"):
        await mgr.create(ticker)
        await mgr.update(ticker)
    dfs = await mgr.get()
    for df in dfs:
        assert isinstance(df, pd.DataFrame)
        assert df.empty
        assert list(df.columns) == [CLOSE, TURNOVER]


@pytest.mark.usefixtures("fake_data_base")
@pytest.mark.asyncio
async def test_not_unique():
    """Некоторые бумаги со старой историей торговались одновременно под несколькими тикерами."""
    mgr = moex.Quotes(("PRMB", "OGKB"))
    for ticker in ("PRMB", "OGKB"):
        await mgr.create(ticker)
        await mgr.update(ticker)
    dfs = await mgr.get()
    for df in dfs:
        assert isinstance(df, pd.DataFrame)
        assert df.index.is_unique
        assert df.index.is_monotonic_increasing


@pytest.fixture()
@pytest.mark.asyncio
async def create_client():
    async with client.Client():
        yield


# noinspection PyProtectedMember
@pytest.mark.usefixtures("create_client")
@pytest.mark.asyncio
async def test_quotes_find_aliases():
    assert set(await moex.Quotes._find_aliases("UPRO")) == {"UPRO", "EONR", "OGK4"}


# noinspection PyTypeChecker
@pytest.mark.usefixtures("create_client")
@pytest.mark.asyncio
async def test_quotes_akrn():
    df = await moex.Quotes("AKRN").get()

    assert isinstance(df, pd.DataFrame)
    assert len(df) > 3000
    assert df.index[0] == pd.Timestamp("2006-10-20")
    assert df[CLOSE].iloc[0] == pytest.approx(834.93)
    assert df[TURNOVER].iloc[0] == pytest.approx(13863.93)
    assert df.index[-1] >= pd.Timestamp("2018-12-07")
    assert df.loc["2014-06-10", TURNOVER] == pytest.approx(20317035.8)
    assert df.loc["2018-09-10", CLOSE] == pytest.approx(4528)


# noinspection PyTypeChecker
@pytest.mark.usefixtures("create_client")
@pytest.mark.asyncio
async def test_quotes_moex():
    df = await moex.Quotes("MOEX").get()

    assert df.shape[0] > 1300
    assert df.index[0] == pd.Timestamp("2013-02-15")
    assert df.loc["2018-03-05", CLOSE] == pytest.approx(117)
    assert df.loc["2018-03-05", TURNOVER] == pytest.approx(533142058.2)


# noinspection PyTypeChecker
@pytest.mark.usefixtures("create_client")
@pytest.mark.asyncio
async def test_quotes_upro():
    df = await moex.Quotes("UPRO").get()

    assert df.shape[0] > 2500
    assert df.index[0] == pd.to_datetime("2007-05-24")
    assert df.iloc[1, 0] == pytest.approx(2.65)
    assert df.iloc[2, 1] == pytest.approx(997822.7)
    assert df.loc["2018-09-07", CLOSE] == pytest.approx(2.633)
    assert df.loc["2018-09-10", TURNOVER] == pytest.approx(24565585)


# noinspection PyTypeChecker
@pytest.mark.usefixtures("create_client")
@pytest.mark.asyncio
async def test_quotes_banep():
    df = await moex.Quotes("BANEP").get()

    assert df.index[0] == pd.to_datetime("2011-11-18")
    assert df.loc["2014-06-10", CLOSE] == pytest.approx(1833.0)
    assert df.loc["2014-06-11", TURNOVER] == pytest.approx(42394025.2)
    assert df.shape[0] > 1000
    assert df.loc["2018-09-07", CLOSE] == pytest.approx(1721.5)
    assert df.loc["2018-09-10", TURNOVER] == pytest.approx(60677908)


# noinspection PyTypeChecker
@pytest.mark.usefixtures("create_client")
@pytest.mark.asyncio
async def test_quotes_sberp():
    df = await moex.Quotes("SBERP").get()

    assert df.shape[0] > 1000
    assert df.index[0] == pd.to_datetime("2007-07-20")
    assert df.loc["2013-03-26", CLOSE] == pytest.approx(72.20)
    assert df.loc["2018-09-10", CLOSE] == pytest.approx(148.36)


# noinspection PyTypeChecker
@pytest.mark.usefixtures("create_client")
@pytest.mark.asyncio
async def test_quotes_gmkn():
    df = await moex.Quotes("GMKN").get()

    assert df.shape[0] > 1000
    assert df.index[0] == pd.to_datetime("2006-12-26")
    assert df.loc["2014-06-09", TURNOVER] == pytest.approx(1496171686)
    assert df.loc["2018-09-07", CLOSE] == pytest.approx(11200)


# noinspection PyTypeChecker
@pytest.mark.usefixtures("create_client")
@pytest.mark.asyncio
async def test_quotes_mstt():
    df = await moex.Quotes("MSTT").get()

    assert df.shape[0] > 1000
    assert df.index[0] == pd.to_datetime("2010-11-03")
    assert df.loc["2013-03-27", CLOSE] == pytest.approx(136.3)
    assert df.loc["2014-06-09", CLOSE] == pytest.approx(110.48)
    assert df.loc["2018-09-07", CLOSE] == pytest.approx(92.0)
    assert df.loc["2018-03-09", CLOSE] == 148.8
    assert df.loc["2018-03-09", TURNOVER] == 439722


# noinspection PyTypeChecker
@pytest.mark.usefixtures("create_client")
@pytest.mark.asyncio
async def test_quotes_kbtk():
    df = await moex.Quotes("KBTK").get()

    assert "2018-03-09" not in df.index
    assert df.loc["2018-03-12", CLOSE] == pytest.approx(145)
    assert df.loc["2018-04-04", TURNOVER] == pytest.approx(11095465)


# noinspection PyTypeChecker
@pytest.mark.usefixtures("create_client")
@pytest.mark.asyncio
async def test_quotes_rtkmp():
    df = await moex.Quotes("RTKMP").get()

    assert df.loc["2018-03-13", TURNOVER] == pytest.approx(24716781)
    assert df.loc["2018-03-13", CLOSE] == pytest.approx(62)
    assert df.loc["2018-04-11", CLOSE] == pytest.approx(60.3)


# noinspection PyTypeChecker
@pytest.mark.usefixtures("create_client")
@pytest.mark.asyncio
async def test_quotes_lsngp():
    df = await moex.Quotes("LSNGP").get()

    assert df.index[0] == pd.Timestamp("2005-08-03")
    assert df.loc["2014-06-09", CLOSE] == pytest.approx(14.7)
    assert df.loc["2014-10-28", TURNOVER] == 1132835
    assert df.loc["2018-09-07", CLOSE] == pytest.approx(86.5)
    assert df.loc["2018-05-31", TURNOVER] == 24798580
    assert df.loc["2018-12-07", CLOSE] == pytest.approx(95.82)


# noinspection PyTypeChecker
@pytest.mark.usefixtures("create_client")
@pytest.mark.asyncio
async def test_quotes_lsrg():
    df = await moex.Quotes("LSRG").get()

    assert df.index[0] == pd.Timestamp("2007-11-30")
    assert df.loc["2018-08-07", CLOSE] == pytest.approx(777)
    assert df.loc["2018-08-10", TURNOVER] == pytest.approx(8626464.5)
    assert df.loc["2018-09-06", CLOSE] == pytest.approx(660)
    assert df.loc["2018-08-28", TURNOVER] == 34666629.5
