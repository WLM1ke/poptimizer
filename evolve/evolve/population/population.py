"""Содержит класс популяции организмов."""
import asyncio
from dataclasses import dataclass, field
from random import random
from typing import Any, AsyncIterator, Final, NamedTuple

import bson
import pandas as pd
from motor.motor_asyncio import AsyncIOMotorCollection

from evolve.population.gene import GenePool, Genotype

_START_POPULATION: Final = 16


class DataProvider:
    """Предоставляет данные, необходимые для построения моделей."""

    async def last_date(self) -> pd.Timestamp:
        """Возвращает последнюю дату торгов."""
        # TODO
        await asyncio.sleep(1)
        return pd.Timestamp("2022-08-18")


@dataclass(kw_only=True, slots=True)
class Organism:
    """Организм."""

    gen: Genotype
    id: bson.ObjectId = field(default_factory=bson.ObjectId)
    timestamp: pd.Timestamp | None = None


Doc = dict[str, Any]  # type: ignore


def _from_doc(doc: Doc) -> Organism:
    return Organism(
        gen=Genotype(doc["gen"]),
        id=doc["_id"],
        timestamp=pd.Timestamp(doc["timestamp"]),
    )


def _to_doc(org: Organism) -> Doc:
    return {
        "gen": org.gen,
        "_id": org.id,
        "timestamp": org.timestamp,
    }


class EvalResult(NamedTuple):
    """Результат оценки организма."""

    desc: str
    dead: bool
    slow: bool


class Population(AsyncIterator[Organism]):
    """Представляет популяцию организмов."""

    def __init__(
        self,
        collection: AsyncIOMotorCollection,
        pool: GenePool,
        provider: DataProvider,
    ):
        """Не создает базовою популяцию - при необходимости создание происходит при первом получении организма."""
        self._collection = collection
        self._geno_pool = pool
        self._date_provider = provider
        self._check_population = True

    def __aiter__(self) -> AsyncIterator[Organism]:
        """Последовательно выдает организмы для эволюционного отбора."""
        return self

    async def __anext__(self) -> Organism:
        """Выдает следующий организм для эволюционного отбора."""
        if self._check_population:
            await self._init()
            self._check_population = False

        last_date = await self._date_provider.last_date()
        pipeline = [
            {"$match": {"timestamp": {"$ne": last_date}}},
            {"$sample": {"size": 1}},
        ]

        if docs := await self._collection.aggregate(pipeline).to_list(1):
            return _from_doc(docs[0])

        pipeline = [
            {"$sample": {"size": 1}},
        ]

        return _from_doc(await anext(self._collection.aggregate(pipeline).to_list(1)))

    async def stats(self) -> list[str]:
        """Представляет информацию о популяции."""
        # TODO
        return ["some population statistics"]

    async def breed(self, org: Organism) -> Organism:
        """Создает и возвращает потомка организма."""
        pipeline = [
            {"$sample": {"size": 2}},
        ]

        parent1, parent2 = await self._collection.aggregate(pipeline).to_list(2)

        child_gen = self._geno_pool.breed(
            org.gen,
            await self._scale(),
            _from_doc(parent1).gen,
            _from_doc(parent2).gen,
        )
        child = Organism(gen=child_gen)

        await self._collection.insert_one(_to_doc(child))

        return child

    async def eval(self, org: Organism) -> EvalResult:
        """Оценивает организм - во время оценки организм может погибнуть."""
        # TODO

        dead = False
        if random() < 0.1:  # noqa: WPS459,S311
            await self._collection.delete_one({"_id": org.id})
            dead = True

        return EvalResult(
            desc="some result",
            dead=dead,
            slow=random() < 0.4,  # noqa: WPS459,WPS432,S311
        )

    async def _init(self) -> None:
        if await self._collection.count_documents({}):
            return

        for _ in range(_START_POPULATION):
            org = Organism(gen=self._geno_pool.new())
            await self._collection.insert_one(_to_doc(org))

    async def _scale(self) -> float:
        count = await self._collection.count_documents({})

        return float(count**0.5)
