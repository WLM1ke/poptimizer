from contextlib import AbstractContextManager

import lmdb
import pytest

from poptimizer.storage import store


@pytest.fixture(scope="module", name="path")
def make_temp_dir(tmpdir_factory):
    return tmpdir_factory.mktemp("store")


def test_context_manager():
    assert issubclass(store.DataStore, AbstractContextManager)


def test_db_closed(path):
    with store.DataStore(path, categories=10) as db:
        pass
    with pytest.raises(lmdb.Error) as error:
        db["a", "b"] = 1
    assert "Attempt to operate on closed/deleted/dropped object." == str(error.value)


def test_put(path):
    with store.DataStore(path, categories=10) as db:
        db["aa"] = 1
        assert db.stat()["entries"] == 1

        db["b"] = 2
        assert db.stat()["entries"] == 2

        db["aa", "first"] = 3
        assert db.stat()["entries"] == 3
        assert db.stat("first")["entries"] == 1

        db["b", "first"] = 4
        assert db.stat()["entries"] == 3
        assert db.stat("first")["entries"] == 2


def test_get(path):
    with store.DataStore(path, categories=10) as db:
        assert db["aa"] == 1
        assert db["b"] == 2
        assert db["aa", "first"] == 3
        assert db["b", "first"] == 4

        db["c"] = 3
        assert db.stat()["entries"] == 4
        assert db.stat("first")["entries"] == 2


def test_get_no_value(path):
    with store.DataStore(path, categories=10) as db:
        assert db["dd"] is None
