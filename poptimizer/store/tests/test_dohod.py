import pandas as pd
import pytest

from poptimizer.config import POptimizerError
from poptimizer.store import dohod
from poptimizer.store.mongo import MONGO_CLIENT


@pytest.fixture(name="manager")
def manager_in_clean_test_db():
    MONGO_CLIENT.drop_database("test")
    yield dohod.Dohod(db="test")
    MONGO_CLIENT.drop_database("test")


def test_dohod(manager):
    df = manager["VSMO"]
    assert isinstance(df, pd.DataFrame)
    assert list(df.columns) == ["VSMO"]
    df = df["VSMO"]
    assert len(df) >= 20
    assert df["2017-10-19"] == 762.68
    assert df["2010-05-21"] == 1.5


def test_dohod2(manager):
    df = manager["GAZP"]
    assert isinstance(df, pd.DataFrame)
    assert list(df.columns) == ["GAZP"]
    df = df["GAZP"]
    assert len(df) >= 15
    assert df["2017-07-20"] == 8.04
    assert df["2010-05-07"] == 2.39
    assert df["2008-05-08"] == 2.66


def test_dohod3(manager):
    df = manager["CHMF"]
    assert isinstance(df, pd.DataFrame)
    assert list(df.columns) == ["CHMF"]
    df = df["CHMF"]
    assert len(df) >= 44
    assert df["2018-06-19"] == 38.32 + 27.72
    assert df["2016-07-05"] == 8.25 + 20.27
    assert df["2019-06-18"] == 35.43


def test_no_html(manager):
    with pytest.raises(POptimizerError) as error:
        # noinspection PyStatementEffect
        manager["TEST"]
    assert "Данные https://www.dohod.ru/ik/analytics/dividend/test не загружены" == str(
        error.value
    )
