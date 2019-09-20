from datetime import date

import pandas as pd
import pytest

from poptimizer.config import POptimizerError
from poptimizer.store import utils, manager, DATE
from poptimizer.store.mongo import MONGO_CLIENT


@pytest.fixture("module", autouse=True)
def drop_test_db():
    MONGO_CLIENT.drop_database("test")
    yield
    MONGO_CLIENT.drop_database("test")


class SimpleManager(manager.AbstractManager):
    LOAD = [{DATE: 1, "col1": 1, "col2": 10}, {DATE: 2, "col1": 2, "col2": 15}]
    UPDATE = [{DATE: 2, "col1": 2, "col2": 15}, {DATE: 4, "col1": 5, "col2": 5}]

    def __init__(self, create_from_scratch=False, validate_last=True):
        super().__init__(
            collection="simple",
            db="test",
            create_from_scratch=create_from_scratch,
            validate_last=validate_last,
        )

    def _download(self, name, last_index):
        if last_index is None or not self._validate_last:
            return self.LOAD
        return self.UPDATE


def test_create():
    mng = SimpleManager()
    # noinspection PyProtectedMember
    collection = mng._mongo.collection

    time0 = pd.Timestamp.now(utils.MOEX_TZ).astimezone(None)
    assert collection.find_one({"_id": "AKRN"}) is None

    data = mng["AKRN"]
    assert isinstance(data, pd.DataFrame)
    assert data.equals(
        pd.DataFrame(data={"col1": [1, 2], "col2": [10, 15]}, index=[1, 2])
    )
    assert collection.find_one({"_id": "AKRN"})["timestamp"] > time0


def test_no_update():
    mng = SimpleManager()
    # noinspection PyProtectedMember
    collection = mng._mongo.collection

    time0 = pd.Timestamp.now(utils.MOEX_TZ).astimezone(None)
    assert collection.find_one({"_id": "AKRN"})["timestamp"] < time0

    data = mng["AKRN"]
    assert isinstance(data, pd.DataFrame)
    assert data.equals(
        pd.DataFrame(data={"col1": [1, 2], "col2": [10, 15]}, index=[1, 2])
    )
    assert collection.find_one({"_id": "AKRN"})["timestamp"] < time0


@pytest.fixture(scope="module")
def next_week_date():
    timestamp = pd.Timestamp.now(utils.MOEX_TZ)
    timestamp += pd.DateOffset(days=7)
    timestamp = timestamp.astimezone(None)
    return timestamp


def test_update(monkeypatch, next_week_date):
    mng = SimpleManager()
    # noinspection PyProtectedMember
    collection = mng._mongo.collection
    monkeypatch.setattr(mng, "LAST_HISTORY_DATE", next_week_date)

    time0 = pd.Timestamp.now(utils.MOEX_TZ).astimezone(None)
    assert collection.find_one({"_id": "AKRN"})["timestamp"] < time0

    data = mng["AKRN"]
    assert isinstance(data, pd.DataFrame)
    assert data.equals(
        pd.DataFrame(data={"col1": [1, 2, 5], "col2": [10, 15, 5]}, index=[1, 2, 4])
    )
    assert collection.find_one({"_id": "AKRN"})["timestamp"] > time0


def test_data_create_from_scratch(monkeypatch, next_week_date):
    mng = SimpleManager(create_from_scratch=True)
    # noinspection PyProtectedMember
    collection = mng._mongo.collection
    monkeypatch.setattr(mng, "LAST_HISTORY_DATE", next_week_date)

    time0 = pd.Timestamp.now(utils.MOEX_TZ).astimezone(None)
    assert collection.find_one({"_id": "AKRN"})["timestamp"] < time0

    data = mng["AKRN"]
    assert isinstance(data, pd.DataFrame)
    assert data.equals(
        pd.DataFrame(data={"col1": [1, 2], "col2": [10, 15]}, index=[1, 2])
    )
    assert collection.find_one({"_id": "AKRN"})["timestamp"] > time0


def test_index_non_unique(monkeypatch):
    mng = SimpleManager()
    monkeypatch.setattr(mng, "LOAD", [{DATE: 1, "col1": 1}, {DATE: 1, "col1": 2}])

    with pytest.raises(POptimizerError) as error:
        # noinspection PyStatementEffect
        mng["RTKM"]
    assert str(error.value) == "Индекс test.simple.RTKM не уникальный"


def test_index_non_increasing(monkeypatch):
    mng = SimpleManager()
    monkeypatch.setattr(mng, "LOAD", [{DATE: 2, "col1": 1}, {DATE: 1, "col1": 2}])

    with pytest.raises(POptimizerError) as error:
        # noinspection PyStatementEffect
        mng["GAZP"]
    assert str(error.value) == "Индекс test.simple.GAZP не возрастает"


def test_validate_all_too_short(monkeypatch, next_week_date):
    mng = SimpleManager(validate_last=False)
    monkeypatch.setattr(mng, "LAST_HISTORY_DATE", next_week_date)
    monkeypatch.setattr(mng, "LOAD", [{DATE: 1, "col1": 2}])

    with pytest.raises(POptimizerError) as error:
        # noinspection PyStatementEffect
        mng["AKRN"]
    assert str(error.value) == "Новые 1 короче старых 2 данных test.simple.AKRN"


def test_data_not_stacks(monkeypatch, next_week_date):
    mng = SimpleManager()
    monkeypatch.setattr(mng, "LAST_HISTORY_DATE", next_week_date)
    monkeypatch.setattr(mng, "UPDATE", [{DATE: 4, "col1": 5, "col2": 5}])

    with pytest.raises(POptimizerError) as error:
        # noinspection PyStatementEffect
        mng["AKRN"]
    assert (
        str(error.value)
        == "Новые {'DATE': 4, 'col1': 5, 'col2': 5} не соответствуют старым "
        "{'DATE': 2, 'col1': 2, 'col2': 15} данным test.simple.AKRN"
    )


def test_validate_all(monkeypatch, next_week_date):
    mng = SimpleManager(validate_last=False)
    monkeypatch.setattr(mng, "LAST_HISTORY_DATE", next_week_date)
    fake_load = [
        {DATE: 1, "col1": 1, "col2": 10},
        {DATE: 2, "col1": 2, "col2": 15},
        {DATE: 7, "col1": 9, "col2": 11},
    ]
    monkeypatch.setattr(mng, "LOAD", fake_load)
    # noinspection PyProtectedMember
    collection = mng._mongo.collection

    time0 = pd.Timestamp.now(utils.MOEX_TZ).astimezone(None)
    assert collection.find_one({"_id": "AKRN"})["timestamp"] < time0

    data = mng["AKRN"]
    assert isinstance(data, pd.DataFrame)
    assert data.equals(
        pd.DataFrame(data={"col1": [1, 2, 9], "col2": [10, 15, 11]}, index=[1, 2, 7])
    )
    assert collection.find_one({"_id": "AKRN"})["timestamp"] > time0


def test_data_formatter():
    data = [{DATE: "2011-02-12", "col1": 1}, {DATE: "2019-09-09", "col1": 2}]
    formatter = {
        DATE: lambda x: (DATE, date.fromisoformat(x)),
        "col1": lambda x: ("col2", x),
    }
    result = [{DATE: date(2011, 2, 12), "col2": 1}, {DATE: date(2019, 9, 9), "col2": 2}]
    assert manager.data_formatter(data, formatter) == result
