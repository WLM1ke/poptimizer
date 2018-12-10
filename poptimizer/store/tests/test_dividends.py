import pandas as pd
import pytest

from poptimizer import config
from poptimizer.store import client
from poptimizer.store.dividends import Dividends


@pytest.fixture(autouse=True)
@pytest.mark.asyncio
async def create_client(tmpdir_factory, monkeypatch):
    temp_dir = tmpdir_factory.mktemp("dividends")
    monkeypatch.setattr(config, "DATA_PATH", temp_dir)
    async with client.Client():
        yield


@pytest.mark.asyncio
async def test_dividends():
    # noinspection PyTypeChecker
    data = await Dividends(("CHMF", "GMKN")).get()

    df0 = data[0]

    assert isinstance(df0, pd.Series)
    isinstance(df0.index, pd.DatetimeIndex)
    assert df0.name == "CHMF"
    assert df0["2018-06-19"] == pytest.approx(38.32 + 27.72)
    assert df0["2017-12-05"] == pytest.approx(35.61)
    assert df0["2010-11-12"] == pytest.approx(4.29)
    assert df0["2011-05-22"] == pytest.approx(2.42 + 3.9)

    df1 = data[1]

    assert df1["2018-07-17"] == pytest.approx(607.98)
    assert df1["2017-10-19"] == pytest.approx(224.2)
    assert df1["2010-05-21"] == pytest.approx(210)
    assert df1["2011-05-16"] == pytest.approx(180)


@pytest.mark.asyncio
async def test_no_data_in_data_base():
    # noinspection PyTypeChecker
    df = await Dividends("TEST").get()
    assert isinstance(df, pd.Series)
    assert df.name == "TEST"
    assert len(df) == 0
    assert isinstance(df.index, pd.DatetimeIndex)
