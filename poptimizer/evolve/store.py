"""Доступ к данным для эволюции."""
from typing import Any, Callable, Final, Optional

import bson
from pymongo.collection import Collection

from poptimizer.config import POptimizerError
from poptimizer.evolve.genotype import Genotype
from poptimizer.store.database import DB, MONGO_CLIENT

# Коллекция для хранения моделей
_COLLECTION = MONGO_CLIENT[DB]["models"]

# Название столбца с индексом
ID: Final = "_id"


def get_collection() -> Collection:
    """Коллекция для хранения моделей."""
    return _COLLECTION


class BaseField:
    """Базовый дескриптор поля.

    Информация об изменениях значения поля сохраняется во вспомогательную переменную для последующих
    инкрементальных обновлений.
    """

    def __init__(self, *, index: bool = False):
        """Для индексируемых полей сохраняет специальное значение названия поля."""
        self._name = index and ID

    def __set_name__(self, owner: type, name: str):
        """Использует специальное имя для индексируемых полей."""
        self._name = self._name or name

    def __set__(self, instance: Any, value: Any):  # noqa: WPS110
        """Сохраняет измененные значение во вспомогательный словарь."""
        data_dict = vars(instance)  # noqa: WPS421
        key = self._name

        update = data_dict["_update"]
        update[key] = value
        data_dict[key] = value

    def __get__(self, instance: Any, owner: type) -> Any:
        """Получает значение атрибута дескриптера."""
        data_dict = vars(instance)  # noqa: WPS421
        try:
            return data_dict[self._name]
        except KeyError as error:
            raise AttributeError(f"'{owner.__name__}' object has no attribute {error}")


class DefaultField(BaseField):
    """Дескриптор поля со значением по умолчанию."""

    def __init__(self, default: Optional[Any] = None):
        """Сохраняет значение поля по умолчанию."""
        super().__init__()
        self._default = default

    def __get__(self, instance: Any, owner: type) -> Any:
        """При отсутствии значения возвращает значение по умолчанию."""
        data_dict = vars(instance)  # noqa: WPS421
        return data_dict.get(self._name, self._default)


class FactoryField(BaseField):
    """Дескриптор поля со значением по умолчанию на основе функции-фабрики."""

    def __init__(self, factory: Callable[[], Any]) -> None:
        """Сохраняет значение фабрики для поля."""
        super().__init__()
        self._factory = factory

    def __get__(self, instance: Any, owner: type) -> Any:
        """При отсутствии значения возвращает результат вызова фабрики."""
        data_dict = vars(instance)  # noqa: WPS421
        return data_dict.get(self._name, self._factory())


class GenotypeField(BaseField):
    """Дескриптор для генотипа."""

    def __set__(self, instance: Any, value: Any):  # noqa: WPS110
        """При необходимости присваиваемое значение преобразуется к типу генотип."""
        if not isinstance(value, Genotype):
            value = Genotype(value)  # noqa: WPS110
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
        """Создает словарь для хранения изменений. Загружает данные по id или создает id."""
        self._update = {}
        if id_ is None:
            self.id = bson.ObjectId()  # noqa: WPS601
            self.genotype = genotype  # noqa: WPS601
        else:
            self._load(id_)

    def save(self) -> None:
        """Сохраняет измененные значения в MongoDB."""
        collection = get_collection()
        update = self._update
        collection.update_one(
            filter={ID: self.id},
            update={"$set": self._update},
            upsert=True,
        )
        update.clear()

    def delete(self) -> None:
        """Удаляет документ из базы."""
        collection = get_collection()
        collection.delete_one({ID: self.id})

    def _load(self, id_: bson.ObjectId) -> None:
        collection = get_collection()
        doc = collection.find_one({ID: id_})

        if doc is None:
            raise IdError(id_)

        for key, value in doc.items():  # noqa: WPS110
            setattr(self, key, value)

        self._update.clear()

    id = BaseField(index=True)
    genotype = GenotypeField()
    wins = DefaultField(0)
    model = DefaultField()
    llh = FactoryField(list)
    ir = FactoryField(list)
    ub = DefaultField(0)
    date = DefaultField()
    timer = DefaultField(0)
    tickers = DefaultField()
