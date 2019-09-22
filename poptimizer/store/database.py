"""Интерфейс для записи и получения данных из  Mongo DB."""
import pickle
from typing import Any

from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database

from poptimizer.store import mongo

# База данных по умолчанию
DB = "data"

# Коллекция для хранения вспомогательной информации и единичных данных
MISC = "misc"

# Ключ для сохранения данных в формате pickle
PICKLE = "pickle"


class MongoDB:
    """Интерфейс для записи и получения данных из  Mongo DB.

    При получении данных может быть указана коллекция. По умолчанию запись будет производиться в
    коллекцию Misc.

    Данные являющиеся корректными документами записываются напрямую, а остальные данные автоматически
    преобразуются в бинарный формат с помощью pickle.
    """

    def __init__(
        self,
        collection: str = MISC,
        db: str = DB,
        client: MongoClient = mongo.MONGO_CLIENT,
    ):
        self._collection = client[db][collection]

    def __getitem__(self, item: str):
        doc = self._collection.find_one({"_id": item})
        if doc is None:
            return doc
        del doc["_id"]
        if PICKLE in doc:
            doc = pickle.loads(doc[PICKLE])
        return doc

    def __setitem__(self, key: str, value: Any):
        try:
            self._collection.replace_one({"_id": key}, value, upsert=True)
        except TypeError:
            value = {PICKLE: pickle.dumps(value)}
            self._collection.replace_one({"_id": key}, value, upsert=True)

    def __delitem__(self, key: str):
        self._collection.delete_one({"_id": key})

    def __len__(self) -> int:
        return self._collection.count_documents({})

    @property
    def client(self) -> MongoClient:
        """Клиент MongoDB."""
        return self._collection.database.client

    @property
    def db(self) -> Database:
        """База данных."""
        return self._collection.database

    @property
    def collection(self) -> Collection:
        """Коллекция для хранения данных."""
        return self._collection
