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
    assert issubclass(store.DataStore, AbstractContextManager)


def test_db_closed():
    with store.DataStore() as db:
        pass
    with pytest.raises(lmdb.Error) as error:
        db["a", "b"] = 1
    assert "Attempt to operate on closed/deleted/dropped object." == str(error.value)


def test_put():
    with store.DataStore() as db:
        db["aa"] = 1
        assert db._env.stat()["entries"] == 1
        db["b"] = 2
        assert db._env.stat()["entries"] == 2
        db["aa", "first"] = 3
        assert db._env.stat()["entries"] == 3
        db["b", "first"] = 4
        assert db._env.stat()["entries"] == 3
        sub_db = db._env.open_db("first".encode())
        with db._env.begin() as txn:
            assert txn.stat(sub_db)["entries"] == 2


def test_get():
    with store.DataStore() as db:
        assert db["aa"] == 1
        assert db["b"] == 2
        assert db["aa", "first"] == 3
        assert db["b", "first"] == 4
        db["c"] = 3
        assert db._env.stat()["entries"] == 4
        sub_db = db._env.open_db("first".encode())
        with db._env.begin() as txn:
            assert txn.stat(sub_db)["entries"] == 2
