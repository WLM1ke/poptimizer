import pandas as pd
import pytest

import poptimizer
from poptimizer import config
from poptimizer.storage import manager, utils
from poptimizer.storage.utils import MOEX_TZ


@pytest.fixture(scope="module", name="path")
def make_temp_dir(tmpdir_factory):
    temp_dir = tmpdir_factory.mktemp("manager")
    return temp_dir


@pytest.fixture(autouse=True)
def fake_data_path(monkeypatch, path):
    monkeypatch.setattr(config, "DATA_PATH", path)


class SimpleManager(manager.AbstractManager):
    LOAD = pd.DataFrame(data={"col1": [1, 2], "col2": [10, 15]})
    UPDATE = pd.DataFrame(data={"col1": [2, 5], "col2": [15, 5]}, index=[1, 2])

    async def _download(self, name):
        if self.data[name] is None:
            return self.LOAD
        return self.UPDATE


def test_data_create():
    time0 = pd.Timestamp.now(MOEX_TZ)
    simple_manager = SimpleManager(("AKRN",), "category")
    data = simple_manager.data
    assert isinstance(data, dict)
    assert len(data) == 1
    assert isinstance(data["AKRN"], utils.Datum)
    assert data["AKRN"].value.equals(
        pd.DataFrame(data={"col1": [1, 2], "col2": [10, 15]})
    )
    assert data["AKRN"].timestamp > time0
    assert simple_manager.names == ("AKRN",)
    assert simple_manager.category == "category"


def test_data_load_with_out_update():
    time0 = pd.Timestamp.now(MOEX_TZ)
    simple_manager = SimpleManager(("AKRN",), "category")
    data = simple_manager.data
    assert isinstance(data, dict)
    assert len(data) == 1
    assert isinstance(data["AKRN"], utils.Datum)
    assert data["AKRN"].value.equals(
        pd.DataFrame(data={"col1": [1, 2], "col2": [10, 15]})
    )
    assert data["AKRN"].timestamp < time0
    assert simple_manager.names == ("AKRN",)
    assert simple_manager.category == "category"


async def fake_update_timestamp():
    return pd.Timestamp.now(MOEX_TZ) + pd.DateOffset(days=1)


def test_fake_update(monkeypatch):
    monkeypatch.setattr(manager.utils, "update_timestamp", fake_update_timestamp)

    time0 = pd.Timestamp.now(MOEX_TZ)
    simple_manager = SimpleManager(("AKRN",), "category")
    data = simple_manager.data
    assert isinstance(data, dict)
    assert len(data) == 1
    assert isinstance(data["AKRN"], utils.Datum)
    assert data["AKRN"].value.equals(
        pd.DataFrame(data={"col1": [1, 2, 5], "col2": [10, 15, 5]})
    )
    assert data["AKRN"].timestamp > time0
    assert simple_manager.names == ("AKRN",)
    assert simple_manager.category == "category"


def test_data_create_from_scratch(monkeypatch):
    monkeypatch.setattr(manager.utils, "update_timestamp", fake_update_timestamp)
    monkeypatch.setattr(SimpleManager, "CREATE_FROM_SCRATCH", True)

    time0 = pd.Timestamp.now(MOEX_TZ)
    simple_manager = SimpleManager(("AKRN", "GAZP"), "category")
    data = simple_manager.data
    assert isinstance(data, dict)
    assert len(data) == 2
    assert isinstance(data["AKRN"], utils.Datum)
    assert data["AKRN"].value.equals(
        pd.DataFrame(data={"col1": [1, 2], "col2": [10, 15]})
    )
    assert data["AKRN"].timestamp > time0
    assert simple_manager.names == ("AKRN", "GAZP")
    assert simple_manager.category == "category"


def test_index_non_unique(monkeypatch):
    monkeypatch.setattr(SimpleManager, "LOAD", pd.DataFrame(index=[1, 1]))

    with pytest.raises(poptimizer.POptimizerError) as error:
        SimpleManager(("RTKM",), "category")
    assert str(error.value) == "Индекс не уникальный"


def test_index_non_monotonic(monkeypatch):
    monkeypatch.setattr(SimpleManager, "LOAD", pd.DataFrame(index=[1, 2, 0]))

    with pytest.raises(poptimizer.POptimizerError) as error:
        SimpleManager(("RTKM",), "category")
    assert str(error.value) == "Индекс не возрастает монотонно"


def test_data_do_not_stacks(monkeypatch):
    bad_update = pd.DataFrame(data={"col1": [3, 5], "col2": [15, 5]}, index=[1, 2])
    monkeypatch.setattr(SimpleManager, "UPDATE", bad_update)
    monkeypatch.setattr(manager.utils, "update_timestamp", fake_update_timestamp)

    with pytest.raises(poptimizer.POptimizerError) as error:
        SimpleManager(("GAZP",), "category")
    error_text = "Существующие данные не соответствуют новым:"
    assert error_text in str(error.value)
