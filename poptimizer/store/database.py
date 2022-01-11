"""Интерфейс для записи и получения данных из Mongo DB."""
import pickle  # noqa: S403
from typing import Any, Final

import pymongo
from poptimizer.shared import connections
# Старые настройки по MongoDB
# _MONGO_URI: Final = "mongodb://localhost:27017"
MONGO_CLIENT: Final = pymongo.MongoClient(connections.MONGO_URI, tz_aware=False)
DB: Final = "data"
MISC: Final = "misc"
_ID: Final = "_id"

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
        client: pymongo.MongoClient = MONGO_CLIENT,
    ):
        """Сохраняется коллекция MongoDB для хранения данных."""
        self._collection = client[db][collection]

    def __getitem__(self, key: str):
        """Получить значение по заданному ключу."""
        doc = self._collection.find_one({"_id": key}, projection={"_id": False})
        if doc is None:
            return doc
        if (pickled_data := doc.get(PICKLE)) is not None:
            doc = pickle.loads(pickled_data)  # noqa: S301
        return doc

    def __setitem__(self, key: str, value: Any):  # noqa: WPS110
        """Сохраняет значение по ключу."""
        try:
            self._collection.replace_one({_ID: key}, value, upsert=True)
        except TypeError:
            value = {PICKLE: pickle.dumps(value)}  # noqa: WPS110
            self._collection.replace_one({_ID: key}, value, upsert=True)

    def __delitem__(self, key: str):  # noqa: WPS603
        """Удаляет значение по ключу в коллекции."""
        self._collection.delete_one({_ID: key})

    def __len__(self) -> int:
        """Количество документов в хранилище."""
        return self._collection.count_documents({})

    def drop(self) -> None:
        """Удалить коллекцию."""
        self._collection.drop()
