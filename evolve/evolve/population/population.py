"""Содержит класс популяции организмов."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Final

import pandas as pd
from motor.motor_asyncio import AsyncIOMotorCollection

from evolve.population.gene import Genotype
from evolve.population.organism import Organism

_MONGO_ID: Final = "_id"
_Doc = dict[str, Any]  # type: ignore


def _from_doc(doc: _Doc) -> Organism:
    if timestamp := doc.get("timestamp"):
        timestamp = pd.Timestamp(timestamp)

    return Organism(
        gen=Genotype(doc["gen"]),
        id=doc[_MONGO_ID],
        timestamp=timestamp,
    )


def _to_doc(org: Organism) -> _Doc:
    doc = {
        "gen": org.gen,
        _MONGO_ID: org.id,
    }

    if org.timestamp:
        doc["timestamp"] = org.timestamp

    return doc


@dataclass(frozen=True, kw_only=True, slots=True)
class PopulationStats:
    """Информация о популяции."""

    timestamp: pd.Timestamp
    count: int
    stats: str
    metrics: pd.DataFrame


class Population:
    """Представляет популяцию организмов.

    Содержит логику хранения организмов в MongoDB и выдаче статистики по ним.
    """

    def __init__(
        self,
        collection: AsyncIOMotorCollection,
    ):
        """Не создает базовою популяцию."""
        self._collection = collection

    async def stats(self) -> PopulationStats:
        """Представляет информацию о популяции."""
        # TODO
        return PopulationStats(
            timestamp=pd.Timestamp("2022-08-19"),
            count=await self._collection.count_documents({}),
            stats="some stats",
            metrics=pd.DataFrame(),
        )

    async def init(self, count: int) -> int:
        """При необходимости инициализируется популяция - возвращается количество созданных организмов."""
        if await self._collection.count_documents({}):
            return 0

        for _ in range(count):
            org = Organism.new()
            await self._collection.insert_one(_to_doc(org))

        return count

    async def next(self, last_date: pd.Timestamp) -> Organism:
        """Выдает следующий организм для эволюционного отбора.

        Отдается предпочтение организмам с датой не равной last_date.
        """
        pipeline = [
            {"$match": {"timestamp": {"$ne": last_date}}},
            {"$sample": {"size": 1}},
        ]

        if docs := await self._collection.aggregate(pipeline).to_list(1):
            return _from_doc(docs[0])

        pipeline = [
            {"$sample": {"size": 1}},
        ]

        docs = await self._collection.aggregate(pipeline).to_list(1)

        return _from_doc(docs[0])

    async def breed(self, org: Organism, scale: int) -> Organism:
        """Создает и возвращает потомка организма."""
        pipeline = [
            {"$sample": {"size": 2}},
        ]

        parent1, parent2 = await self._collection.aggregate(pipeline).to_list(2)

        child = org.breed(scale, _from_doc(parent1), _from_doc(parent2))

        await self._collection.insert_one(_to_doc(child))

        return child

    async def update(self, org: Organism) -> None:
        """Обновляет данные организма."""
        await self._collection.replace_one(
            filter={_MONGO_ID: org.id},
            replacement=_to_doc(org),
            upsert=True,
        )

    async def delete(self, org: Organism) -> None:
        """Удаляет организм из популяции."""
        await self._collection.delete_one({_MONGO_ID: org.id})
