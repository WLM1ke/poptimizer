import pandas as pd
import pytest

from poptimizer.config import POptimizerError
from poptimizer.store import smart_lab, DATE, TICKER, DIVIDENDS
from poptimizer.store.mongo import MONGO_CLIENT
from poptimizer.store.smart_lab import SMART_LAB


@pytest.fixture(name="manager")
def manager_in_clean_test_db():
    MONGO_CLIENT.drop_database("test")
    yield smart_lab.SmartLab(db="test")
    MONGO_CLIENT.drop_database("test")


def test_smart_lab(manager):
    df = manager[SMART_LAB]
    assert isinstance(df, pd.DataFrame)
    assert df.index.name == DATE
    assert list(df.columns) == [TICKER, DIVIDENDS]
    assert df.dtypes[DIVIDENDS] == float


def test_smart_lab_bad_url(monkeypatch, manager):
    monkeypatch.setattr(smart_lab, "URL", "https://smart-lab.ru/dividends12")
    with pytest.raises(POptimizerError) as error:
        # noinspection PyStatementEffect
        manager[SMART_LAB]
    assert str(error.value) == "Данные https://smart-lab.ru/dividends12 не загружены"


def test_smart_lab_bad_collection(manager):
    with pytest.raises(POptimizerError) as error:
        # noinspection PyStatementEffect
        manager["QQQ"]
    assert "Отсутствуют данные test.misc.QQQ" == str(error.value)
