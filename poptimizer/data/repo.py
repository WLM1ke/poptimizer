"""Реализация репозитория для таблиц."""
import pandas as pd
from motor.motor_asyncio import AsyncIOMotorDatabase

from poptimizer.data import domain


class Repo:
    """Репозиторий для хранения таблиц."""

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        """Сохраняет ссылку на базу."""
        self._db = db

    async def get(self, group: domain.Group, name: str | None = None) -> domain.Table:
        """Загружает таблицу."""
        collection = self._db[group.value]
        id_ = name or group.value

        doc = await collection.find_one(
            {"_id": id_},
            projection={"_id": False},
        )
        doc = doc or {}

        if df := doc.get("df"):
            df = pd.DataFrame.from_dict(df, orient="records")

        return domain.Table(
            group=group,
            name=name,
            timestamp=doc.get("timestamp"),
            df=df,
        )

    async def save(self, table: domain.Table) -> None:
        """Сохраняет таблицу."""
        collection = self._db[table.group.value]
        id_ = table.name or table.group.value

        doc = {
            "timestamp": table.timestamp,
        }

        if table.df is not None:
            doc["df"] = table.df.to_dict(orient="records")

        await collection.replace_one(
            filter={"_id": id_},
            replacement=doc,
            upsert=True,
        )
