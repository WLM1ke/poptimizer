"""Доступ к данным для эволюции."""
from typing import Any, Type, Optional, NoReturn

import bson
from pymongo.collection import Collection

from poptimizer.config import POptimizerError
from poptimizer.evolve.genotype import Genotype
from poptimizer.store.mongo import DB, MONGO_CLIENT

# Коллекция для хранения моделей
_COLLECTION = MONGO_CLIENT[DB]["models"]

# Название столбца с индексом
ID = "_id"


def get_collection() -> Collection:
    """Коллекция для хранения моделей."""
    return _COLLECTION


class BaseField:
    """Базовый дескриптор поля.

    Информация об изменениях значения поля сохраняется в вспомогательную переменную для последующих
    инкрементальных апдейтов.
    """

    def __init__(self, *, index: bool = False):
        self._name = index and ID

    def __set_name__(self, owner: Type, name: str):
        self._name = self._name or name

    def __set__(self, instance: Any, value: Any):
        """Сохраняет измененные значение во вспомогательный словарь."""
        data_dict = vars(instance)
        key = self._name

        update = data_dict["_update"]
        update[key] = value
        data_dict[key] = value

    def __get__(self, instance: Any, owner: Type) -> Any:
        try:
            data_dict = vars(instance)
            return data_dict[self._name]
        except KeyError as error:
            raise AttributeError(f"'{owner.__name__}' object has no attribute {error}")


class DefaultField(BaseField):
    """Дескриптор поля со значением по умолчанию."""

    def __init__(self, default: Optional[Any] = None):
        super().__init__()
        self._default = default

    def __get__(self, instance: Any, owner: Type) -> Any:
        data_dict = vars(instance)
        return data_dict.get(self._name, self._default)


class GenotypeField(BaseField):
    """Дескриптор для генотипа.

    При необходимости присваиваемое значение преобразуется к типу генотип.
    """

    def __set__(self, instance: Any, value: Any):
        if not isinstance(value, Genotype):
            value = Genotype(value)
        super().__set__(instance, value)


class IdError(POptimizerError):
    """Ошибка попытки загрузить ID, которого нет в MongoDB."""


class Doc:
    """Документ в базе данных."""

    def __init__(
        self,
        *,
        id_: Optional[bson.ObjectId] = None,
        genotype: Optional[Genotype] = None,
    ):
        self._update = {}
        if id_ is None:
            self.id = bson.ObjectId()
            self.genotype = genotype
        else:
            self._load(id_)

    def _load(self, id_: bson.ObjectId) -> NoReturn:
        collection = get_collection()
        doc = collection.find_one({ID: id_})

        if doc is None:
            raise IdError(id_)

        for key, value in doc.items():
            setattr(self, key, value)

        self._update.clear()

    def save(self) -> NoReturn:
        """Сохраняет измененные значения в MongoDB."""
        collection = get_collection()
        update = self._update
        collection.update_one(filter={ID: self.id}, update={"$set": self._update}, upsert=True)
        update.clear()

    def delete(self) -> NoReturn:
        """Удаляет документ из базы."""
        collection = get_collection()
        collection.delete_one({ID: self.id})

    id = BaseField(index=True)
    genotype = GenotypeField()
    wins = DefaultField(0)
    model = DefaultField()
    llh = BaseField()
    date = DefaultField()
    timer = DefaultField(0)
    tickers = DefaultField()
