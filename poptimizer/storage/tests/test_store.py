from contextlib import AbstractContextManager

import lmdb
import pytest

from poptimizer import config
from poptimizer.storage import store


@pytest.fixture(scope="module")
def make_temp_dir(tmpdir_factory):
    return tmpdir_factory.mktemp("store")


@pytest.fixture(autouse=True)
def fake_data_path(make_temp_dir, monkeypatch):
    monkeypatch.setattr(config, "DATA_PATH", make_temp_dir)


def test_context_manager():
    assert isinstance(store.DataStore(), AbstractContextManager)


def test_db_closed():
    with store.DataStore() as db:
        pass
    with pytest.raises(lmdb.Error) as error:
        db["a", "b"] = 1
    assert "Attempt to operate on closed/deleted/dropped object." == str(error.value)


def test_put():
    with store.DataStore() as db:
        db[None, "a"] = 1
        assert db._env.stat()["entries"] == 1
        db[None, "b"] = 2
        assert db._env.stat()["entries"] == 2
        db["first", "a"] = 3
        assert db._env.stat()["entries"] == 3
        db["first", "b"] = 4
        assert db._env.stat()["entries"] == 3


def test_get():
    with store.DataStore() as db:
        assert db[None, "a"] == 1
        assert db[None, "b"] == 2
        assert db["first", "a"] == 3
        assert db["first", "b"] == 4
        db[None, "c"] = 3
        assert db._env.stat()["entries"] == 4
