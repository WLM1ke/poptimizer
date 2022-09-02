"""Реализация репозитория для таблиц."""
from typing import Any, ClassVar, Final, Protocol, TypeVar

from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import ValidationError
from pymongo.errors import PyMongoError

from poptimizer.data import domain, exceptions

_MONGO_ID: Final = "_id"

Table_co = TypeVar("Table_co", covariant=True)


class Table(Protocol[Table_co]):
    """Таблица с рыночными данными.

    Таблицы разбиты на группы, некоторые из которых содержат единственный элемент. В таком случае название элемента
    не указывается.
    """

    group: ClassVar[domain.Group]
    id_: str

    @classmethod
    def parse_obj(cls, doc: dict[str, Any]) -> Table_co:
        """Восстанавливает таблицу из словаря."""

    def dict(self) -> dict[str, Any]:
        """Преобразует таблицу в словарь для последующего восстановления."""


class Repo:
    """Репозиторий для хранения таблиц.

    При сохранении валидирует данные.
    """

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._db = db

    async def get(self, table_type: type[Table[Table_co]], id_: str | None = None) -> Table_co:
        """Загружает таблицу."""
        collection = self._db[table_type.group]
        id_ = id_ or table_type.group

        try:
            doc = await collection.find_one({_MONGO_ID: id_})
        except PyMongoError as err:
            raise exceptions.LoadError(table_type.group, id_) from err

        return table_type.parse_obj(doc or {_MONGO_ID: id_})

    async def save(self, table: Table[Table_co]) -> None:
        """Валидирует и сохраняет таблицу."""
        doc = _validate(table)

        collection = self._db[table.group]

        try:
            await collection.replace_one(
                filter={_MONGO_ID: table.id_},
                replacement=doc,
                upsert=True,
            )
        except PyMongoError as err:
            raise exceptions.SaveError(table.group, table.id_) from err


def _validate(table: Table[Table_co]) -> dict[str, Any]:
    doc = table.dict()

    try:
        table.parse_obj(doc | {_MONGO_ID: table.id_})
    except ValidationError as err_val:
        raise exceptions.SaveError(table.group, table.id_) from err_val

    return doc
