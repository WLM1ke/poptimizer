import pandas as pd
import pytest

from poptimizer import config
from poptimizer.config import POptimizerError
from poptimizer.store import client, smart_lab, DATE, TICKER, DIVIDENDS


@pytest.fixture(autouse=True)
@pytest.mark.asyncio
async def create_client(tmpdir_factory, monkeypatch):
    temp_dir = tmpdir_factory.mktemp("smart_lab")
    monkeypatch.setattr(config, "DATA_PATH", temp_dir)
    async with client.Client():
        yield


@pytest.mark.asyncio
async def test_smart_lab():
    df = await smart_lab.SmartLab().get()
    assert isinstance(df, pd.DataFrame)
    assert df.index.name == DATE
    assert list(df.columns) == [TICKER, DIVIDENDS]
    assert df.dtypes[DIVIDENDS] == float


@pytest.mark.asyncio
async def test_smart_lab_raise(monkeypatch):
    monkeypatch.setattr(smart_lab, "URL", "https://smart-lab.ru/dividends1")
    with pytest.raises(POptimizerError) as error:
        await smart_lab.SmartLab().get()
    assert str(error.value) == "Данные https://smart-lab.ru/dividends1 не загружены"
