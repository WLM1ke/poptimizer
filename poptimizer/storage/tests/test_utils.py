import dataclasses
import pathlib

import aiomoex
import pandas as pd
import pytest

from poptimizer import config
from poptimizer.storage import utils, store
from poptimizer.storage.store import MAX_SIZE, MAX_DBS


def test_data():
    time0 = pd.Timestamp.now(utils.MOEX_TZ)
    data = utils.Datum(42)
    time1 = pd.Timestamp.now(utils.MOEX_TZ)
    assert data.value == 42
    assert time0 <= data.timestamp <= time1
    with pytest.raises(dataclasses.FrozenInstanceError) as error:
        # noinspection PyDataclass
        data.value = 24
    assert "cannot assign to field 'value'" in str(error.value)


@pytest.mark.asyncio
async def test_download_last_history():
    async with aiomoex.ISSClientSession():
        date = await utils.download_last_history()
    assert isinstance(date, pd.Timestamp)
    assert date.hour == 19
    assert date.minute == 45
    assert date.second == 0
    assert date.microsecond == 0
    assert date.nanosecond == 0
    now = pd.Timestamp.now("Europe/Moscow")
    assert date < pd.Timestamp.now("Europe/Moscow")
    # noinspection PyUnresolvedReferences
    assert date.tz == now.tz


@pytest.fixture(scope="module", name="path")
def make_temp_dir(tmpdir_factory):
    return pathlib.Path(tmpdir_factory.mktemp("utils"))


@pytest.mark.asyncio
async def test_update_timestamp(path, monkeypatch):
    monkeypatch.setattr(config, "DATA_PATH", path)
    async with aiomoex.ISSClientSession():
        date = await utils.update_timestamp()
        date_web = await utils.download_last_history()
    with store.DataStore(path, MAX_SIZE, MAX_DBS) as db:
        date_store = db[utils.LAST_HISTORY].value
    assert date == date_web == date_store


@pytest.mark.asyncio
async def test_update_timestamp_after_end_of_trading_day(path, monkeypatch):
    monkeypatch.setattr(config, "DATA_PATH", path)
    fake_end_of_trading = dict(hour=0, minute=0, second=0, microsecond=0, nanosecond=0)
    async with aiomoex.ISSClientSession():
        date_web = await utils.download_last_history()
        monkeypatch.setattr(utils, "END_OF_TRADING", fake_end_of_trading)
        date = await utils.update_timestamp()
    with store.DataStore(path, MAX_SIZE, MAX_DBS) as db:
        date_store = db[utils.LAST_HISTORY].value
    assert date == date_web == date_store
