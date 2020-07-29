import pytest
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database

from poptimizer.store import database
from poptimizer.store.mongo import MONGO_CLIENT


@pytest.fixture(scope="module", autouse=True)
def drop_test_db():
    MONGO_CLIENT.drop_database("test")
    yield
    MONGO_CLIENT.drop_database("test")


def test_mongodb_valid_data():
    mongo = database.MongoDB("main", "test")

    assert isinstance(mongo.collection, Collection)
    assert mongo.collection.name == "main"
    assert isinstance(mongo.db, Database)
    assert mongo.db.name == "test"
    assert isinstance(mongo.client, MongoClient)
    assert mongo.client is MONGO_CLIENT

    assert len(mongo) == 0
    value = dict(q=1, w="text")
    mongo["key"] = value
    assert mongo["key"] == value
    assert len(mongo) == 1

    del mongo["key"]
    assert mongo["key"] is None
    assert len(mongo) == 0


def test_mongodb_not_valid_data():
    mongo = database.MongoDB("main", "test")

    assert isinstance(mongo.collection, Collection)
    assert mongo.collection.name == "main"
    assert isinstance(mongo.db, Database)
    assert mongo.db.name == "test"
    assert isinstance(mongo.client, MongoClient)
    assert mongo.client is MONGO_CLIENT

    assert len(mongo) == 0
    value = [dict(q=1, w="text")]
    mongo["key"] = value
    assert mongo["key"] == value
    assert len(mongo) == 1

    del mongo["key"]
    assert mongo["key"] is None
    assert len(mongo) == 0
