"""Интерфейс для записи и получения данных из  Mongo DB."""
import pickle
from typing import Dict, Any

import pymongo
from pymongo.errors import InvalidDocument

from poptimizer.store import mongo

# Коллекция для хранения вспомогательной информации и единичных данных
MISC = "misc"

# Ключ для сохранения данных в формате pickle
PICKLE = "pickle"


class DB:
    """Интерфейс для записи и получения данных из  Mongo DB.

    При получении данных может быть указана коллекция. По умолчанию запись будет производиться в
    коллекцию Misc.

    Данные являющиеся корректными документами записываются напрямую, а остальные данные автоматически
    преобразуются в бинарный формат с помощью pickle.
    """

    def __init(
        self, collection: str = MISC, client: pymongo.MongoClient = mongo.MONGO_CLIENT
    ):
        self._collection = client[collection]

    def __getitem__(self, item: str):
        doc = self._collection.find_one({"_id": item})
        del doc["_id"]
        if PICKLE in doc:
            doc = pickle.loads(doc[PICKLE])
        return doc

    def __setitem__(self, key: str, value: Dict[str, Any]):
        try:
            self._collection.replace_one({"_id": key}, value, upsert=True)
        except InvalidDocument:
            value = {PICKLE: pickle.dumps(value)}
            self._collection.replace_one({"_id": key}, value, upsert=True)

    def __delitem__(self, key: str):
        self._collection.delete_one({"_id": key})
