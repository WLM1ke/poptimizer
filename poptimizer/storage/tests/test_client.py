import lmdb
import pandas as pd
import pytest

from poptimizer import config
from poptimizer.storage import manager, client


@pytest.fixture(scope="module", name="path")
def make_temp_dir(tmpdir_factory):
    temp_dir = tmpdir_factory.mktemp("client")
    return temp_dir


@pytest.fixture(autouse=True)
def fake_data_path(path, monkeypatch):
    monkeypatch.setattr(config, "DATA_PATH", path)
    yield


RESULT = pd.DataFrame(data={"col1": [1, 2], "col2": [10, 15]})


class Simple(manager.AbstractManager):
    async def _download(self, name):
        return pd.DataFrame(RESULT)


# noinspection PyProtectedMember
@pytest.mark.asyncio
async def test_client():
    async with client.Client() as db:
        data = db.simple(("AKRN",), "category")
        df = await data.get()
    assert df.equals(RESULT)
    assert db._session.closed
    with pytest.raises(lmdb.Error) as error:
        db._store._env.info()
    assert str(error.value) == "Attempt to operate on closed/deleted/dropped object."


@pytest.mark.asyncio
async def test_client_access_to_wrong_manager():
    with pytest.raises(AttributeError) as error:
        async with client.Client() as db:
            db.wrong(("AKRN",), "category")
    assert str(error.value) == "Отсутствует менеджер данных для 'wrong'."
