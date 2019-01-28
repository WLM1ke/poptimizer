import pandas as pd
import pytest

from poptimizer import config
from poptimizer.config import POptimizerError
from poptimizer.store import client, dohod


@pytest.fixture(autouse=True)
@pytest.mark.asyncio
async def create_client(tmpdir_factory, monkeypatch):
    temp_dir = tmpdir_factory.mktemp("dohod")
    monkeypatch.setattr(config, "DATA_PATH", temp_dir)
    async with client.Client():
        yield


@pytest.mark.asyncio
async def test_dohod():
    df = await dohod.Dohod(("VSMO",)).get()
    assert isinstance(df, pd.Series)
    assert len(df) >= 21
    assert df["2017-10-19"] == 762.68
    assert df["2004-03-29"] == 11


@pytest.mark.asyncio
async def test_dohod2():
    df = await dohod.Dohod(("GAZP",)).get()
    assert isinstance(df, pd.Series)
    assert len(df) >= 16
    assert df["2004-05-07"] == 0.69
    assert df["2017-07-20"] == 8.04
    assert df["2008-05-08"] == 2.66


@pytest.mark.asyncio
async def test_no_html():
    with pytest.raises(POptimizerError) as error:
        await dohod.Dohod(("TEST",)).get()
    assert "Данные https://www.dohod.ru/ik/analytics/dividend/test не загружены" == str(
        error.value
    )


@pytest.mark.asyncio
async def test_no_dividends_table_in_html():
    with pytest.raises(POptimizerError) as error:
        await dohod.Dohod(("MSRS",)).get()
    assert "На странице нет таблицы 2" == str(error.value)
