import pandas as pd
import pytest

from poptimizer.store import dividends_new
from poptimizer.store.mongo import MONGO_CLIENT


@pytest.fixture("module", name="manager")
def manager_in_clean_test_db():
    MONGO_CLIENT.drop_database("test")
    yield dividends_new.Dividends(db="test")
    MONGO_CLIENT.drop_database("test")


def test_dividends(manager):
    df = manager["CHMF"]
    assert isinstance(df, pd.DataFrame)
    isinstance(df.index, pd.DatetimeIndex)
    assert df.loc["2018-06-19", "CHMF"] == pytest.approx(38.32 + 27.72)
    assert df.loc["2017-12-05", "CHMF"] == pytest.approx(35.61)
    assert df.loc["2010-11-12", "CHMF"] == pytest.approx(4.29)
    assert df.loc["2011-05-22", "CHMF"] == pytest.approx(2.42 + 3.9)

    df = manager["GMKN"]
    assert df.loc["2018-07-17", "GMKN"] == pytest.approx(607.98)
    assert df.loc["2017-10-19", "GMKN"] == pytest.approx(224.2)
    assert df.loc["2010-05-21", "GMKN"] == pytest.approx(210)
    assert df.loc["2011-05-16", "GMKN"] == pytest.approx(180)


def test_no_data_in_data_base(manager):
    df = manager["TEST"]
    assert isinstance(df, pd.DataFrame)
    assert df.empty
