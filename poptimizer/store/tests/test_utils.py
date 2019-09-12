import apimoex
import pandas as pd
import pytest

from poptimizer.store import utils_new, mongo


@pytest.fixture("module", autouse=True)
def drop_test_db():
    mongo.MONGO_CLIENT.drop_database("test")
    yield
    mongo.MONGO_CLIENT.drop_database("test")


def test_now_and_end_of_trading_day_previous(monkeypatch):
    monkeypatch.setattr(
        utils_new.pd.Timestamp,
        "now",
        lambda x: pd.Timestamp(
            year=2019, month=5, day=4, hour=19, minute=44, tz=utils_new.MOEX_TZ
        ),
    )
    now, end_of_trading = utils_new.now_and_end_of_trading_day()

    assert now.tzinfo is None
    assert end_of_trading.tzinfo is None

    assert now == pd.Timestamp(year=2019, month=5, day=4, hour=16, minute=44)
    assert end_of_trading == pd.Timestamp(year=2019, month=5, day=3, hour=16, minute=45)


def test_now_and_end_of_trading_day_this_day(monkeypatch):
    monkeypatch.setattr(
        utils_new.pd.Timestamp,
        "now",
        lambda x: pd.Timestamp(
            year=2019, month=5, day=4, hour=19, minute=46, tz=utils_new.MOEX_TZ
        ),
    )
    now, end_of_trading = utils_new.now_and_end_of_trading_day()

    assert now.tzinfo is None
    assert end_of_trading.tzinfo is None

    assert now == pd.Timestamp(year=2019, month=5, day=4, hour=16, minute=46)
    assert end_of_trading == pd.Timestamp(year=2019, month=5, day=4, hour=16, minute=45)


def test_last_history_from_doc():
    date = utils_new.last_history_from_doc({"data": [{"till": "2019-09-10"}]})
    assert date.tzinfo is None
    assert date == pd.Timestamp(year=2019, month=9, day=10, hour=16, minute=45)


def test_get_last_history_date(monkeypatch):
    collection = mongo.MONGO_CLIENT["test"]["qqq"]
    monkeypatch.setattr(
        apimoex,
        "get_board_dates",
        lambda x, board, market, engine: [{"till": "2019-09-10"}],
    )

    time0 = pd.Timestamp.now(utils_new.MOEX_TZ).astimezone(None)
    assert collection.find_one({"_id": "last_date"}) is None

    date = utils_new.get_last_history_date(db="test", collection="qqq")

    assert date == pd.Timestamp(year=2019, month=9, day=10, hour=16, minute=45)

    assert collection.find_one({"_id": "last_date"})["timestamp"] > time0
