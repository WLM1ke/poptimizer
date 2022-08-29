"""Реализация репозитория для таблиц."""
from typing import Any, ClassVar, Protocol, TypeVar

from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import ValidationError
from pymongo.errors import PyMongoError

from poptimizer.data import domain, exceptions

Table_co = TypeVar("Table_co", covariant=True)


class Table(Protocol[Table_co]):
    """Таблица с рыночными данными.

    Таблицы разбиты на группы, некоторые из которых содержат единственный элемент. В таком случае название элемента
    не указывается.
    """

    group: ClassVar[domain.Group]
    id_: str | None

    @classmethod
    def parse_obj(cls, doc: dict[str, Any]) -> Table_co:
        """Восстанавливает таблицу из словаря."""

    def dict(self) -> dict[str, Any]:
        """Преобразует таблицу в словарь для последующего восстановления."""


class Repo:
    """Репозиторий для хранения таблиц."""

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._db = db

    async def get(self, table_type: type[Table[Table_co]], id_: str | None = None) -> Table_co:
        """Загружает таблицу."""
        collection = self._db[table_type.group]
        id_ = id_ or table_type.group

        try:
            doc = await collection.find_one({"_id": id_})
        except PyMongoError as err:
            raise exceptions.LoadError(table_type.group, id_) from err

        try:
            return table_type.parse_obj(doc or {"_id": id_})
        except ValidationError as err_val:
            raise exceptions.LoadError(table_type.group, id_) from err_val

    async def save(self, table: Table[Table_co]) -> None:
        """Сохраняет таблицу."""
        collection = self._db[table.group]
        id_ = table.id_ or table.group

        try:
            await collection.replace_one(
                filter={"_id": id_},
                replacement=table.dict(),
                upsert=True,
            )
        except PyMongoError as err:
            raise exceptions.SaveError(table.group, table.id_) from err
