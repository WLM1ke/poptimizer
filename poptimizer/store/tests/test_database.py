import pytest
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database

from poptimizer.store import MONGO_CLIENT, db


@pytest.fixture("module", autouse=True)
def drop_test_db():
    MONGO_CLIENT.drop_database("test")
    yield
    MONGO_CLIENT.drop_database("test")


def test_mongodb_valid_data():
    mongo = db.MongoDB("main", "test")

    assert isinstance(mongo.collection, Collection)
    assert mongo.collection.name == "main"
    assert isinstance(mongo.db, Database)
    assert mongo.db.name == "test"
    assert isinstance(mongo.client, MongoClient)
    assert mongo.client is MONGO_CLIENT

    value = dict(q=1, w="text")
    mongo["key"] = value
    assert mongo["key"] == value

    del mongo["key"]
    assert mongo["key"] is None


def test_mongodb_not_valid_data():
    mongo = db.MongoDB("main", "test")

    assert isinstance(mongo.collection, Collection)
    assert mongo.collection.name == "main"
    assert isinstance(mongo.db, Database)
    assert mongo.db.name == "test"
    assert isinstance(mongo.client, MongoClient)
    assert mongo.client is MONGO_CLIENT

    value = [dict(q=1, w="text")]
    mongo["key"] = value
    assert mongo["key"] == value

    del mongo["key"]
    assert mongo["key"] is None
