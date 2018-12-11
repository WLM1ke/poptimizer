import aiomoex
import pandas as pd
import pytest

import poptimizer
from poptimizer.store import manager, lmbd
from poptimizer.store.client import MAX_SIZE, MAX_DBS

# noinspection PyProtectedMember
from poptimizer.store.utils import MOEX_TZ


@pytest.fixture(scope="module", name="path")
def make_temp_dir(tmpdir_factory):
    temp_dir = tmpdir_factory.mktemp("manager")
    return temp_dir


@pytest.fixture(autouse=True)
@pytest.mark.asyncio
async def fake_data_path(path):
    async with aiomoex.ISSClientSession() as session:
        with lmbd.DataStore(path, MAX_SIZE, MAX_DBS) as db:
            manager.AbstractManager.ISS_SESSION = session
            manager.AbstractManager.STORE = db
            yield


class SimpleManager(manager.AbstractManager):
    LOAD = pd.DataFrame(data={"col1": [1, 2], "col2": [10, 15]})
    UPDATE = pd.DataFrame(data={"col1": [2, 5], "col2": [15, 5]}, index=[1, 2])

    async def _download(self, name):
        if self._data[name] is None:
            return self.LOAD
        return self.UPDATE


# noinspection PyProtectedMember
@pytest.mark.asyncio
async def test_data_create():
    time0 = pd.Timestamp.now(MOEX_TZ)
    simple_manager = SimpleManager(("AKRN",), "category")

    assert simple_manager._last_history_date is None

    data = await simple_manager.get()

    assert isinstance(simple_manager._last_history_date, str)
    assert len(simple_manager._last_history_date) == 10
    assert simple_manager._last_history_date >= "2018-12-10"

    assert isinstance(data, pd.DataFrame)
    assert data.equals(pd.DataFrame(data={"col1": [1, 2], "col2": [10, 15]}))
    # noinspection PyProtectedMember
    assert simple_manager._data["AKRN"].timestamp > time0
    assert simple_manager.names == ("AKRN",)
    assert simple_manager.category == "category"


@pytest.mark.asyncio
async def test_data_load_with_out_update():
    time0 = pd.Timestamp.now(MOEX_TZ)
    simple_manager = SimpleManager("AKRN", "category")
    data = await simple_manager.get()
    assert isinstance(data, pd.DataFrame)
    assert data.equals(pd.DataFrame(data={"col1": [1, 2], "col2": [10, 15]}))
    # noinspection PyProtectedMember
    assert simple_manager._data["AKRN"].timestamp < time0
    assert simple_manager.names == ("AKRN",)
    assert simple_manager.category == "category"


@pytest.mark.asyncio
async def fake_update_timestamp(_):
    return pd.Timestamp.now(MOEX_TZ) + pd.DateOffset(days=1)


@pytest.mark.asyncio
async def test_fake_update(monkeypatch):
    monkeypatch.setattr(manager.utils, "update_timestamp", fake_update_timestamp)

    time0 = pd.Timestamp.now(MOEX_TZ)
    simple_manager = SimpleManager(("AKRN",), "category")
    data = await simple_manager.get()
    assert isinstance(data, pd.DataFrame)
    assert data.equals(pd.DataFrame(data={"col1": [1, 2, 5], "col2": [10, 15, 5]}))
    # noinspection PyProtectedMember
    assert simple_manager._data["AKRN"].timestamp > time0
    assert simple_manager.names == ("AKRN",)
    assert simple_manager.category == "category"


@pytest.mark.asyncio
async def test_data_create_from_scratch(monkeypatch):
    monkeypatch.setattr(manager.utils, "update_timestamp", fake_update_timestamp)
    monkeypatch.setattr(SimpleManager, "CREATE_FROM_SCRATCH", True)

    time0 = pd.Timestamp.now(MOEX_TZ)
    # noinspection PyTypeChecker
    simple_manager = SimpleManager(("AKRN", "GAZP"), "category")
    data = await simple_manager.get()
    assert isinstance(data, list)
    assert len(data) == 2
    assert isinstance(data[0], pd.DataFrame)
    assert data[0].equals(pd.DataFrame(data={"col1": [1, 2], "col2": [10, 15]}))
    # noinspection PyProtectedMember
    assert simple_manager._data["AKRN"].timestamp > time0
    assert simple_manager.names == ("AKRN", "GAZP")
    assert simple_manager.category == "category"


@pytest.mark.asyncio
async def test_index_non_unique(monkeypatch):
    monkeypatch.setattr(SimpleManager, "LOAD", pd.DataFrame(index=[1, 1]))

    with pytest.raises(poptimizer.POptimizerError) as error:
        await SimpleManager(("RTKM",), "category").get()
    assert str(error.value) == "Индекс RTKM не уникальный"


@pytest.mark.asyncio
async def test_index_non_monotonic(monkeypatch):
    monkeypatch.setattr(SimpleManager, "LOAD", pd.DataFrame(index=[1, 2, 0]))

    with pytest.raises(poptimizer.POptimizerError) as error:
        await SimpleManager(("RTKM",), "category").get()
    assert str(error.value) == "Индекс RTKM не возрастает монотонно"


@pytest.mark.asyncio
async def test_data_do_not_stacks(monkeypatch):
    bad_update = pd.DataFrame(data={"col1": [3, 5], "col2": [15, 5]}, index=[1, 2])
    monkeypatch.setattr(SimpleManager, "UPDATE", bad_update)
    monkeypatch.setattr(manager.utils, "update_timestamp", fake_update_timestamp)

    with pytest.raises(poptimizer.POptimizerError) as error:
        await SimpleManager(("GAZP",), "category").get()
    error_text = "Существующие данные не соответствуют новым:"
    assert error_text in str(error.value)
