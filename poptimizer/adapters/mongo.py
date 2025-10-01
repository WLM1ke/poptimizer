import datetime
import random
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any, Final

import pymongo
from pydantic import MongoDsn, ValidationError
from pymongo.asynchronous import collection, database
from pymongo.errors import PyMongoError

from poptimizer import consts, errors
from poptimizer.adapters import adapter
from poptimizer.domain import domain
from poptimizer.domain.evolve import evolve

_MONGO_ID: Final = "_id"
REV: Final = "rev"
VER: Final = "ver"
UID: Final = "uid"
DAY: Final = "day"

type MongoDocument = dict[str, Any]
type MongoClient = pymongo.AsyncMongoClient[MongoDocument]
type MongoDatabase = database.AsyncDatabase[MongoDocument]
type MongoCollection = collection.AsyncCollection[MongoDocument]


@asynccontextmanager
async def db(uri: MongoDsn, db: str) -> AsyncIterator[MongoDatabase]:
    mongo_client: MongoClient = pymongo.AsyncMongoClient(str(uri), tz_aware=False)
    try:
        yield mongo_client[db]
    finally:
        await mongo_client.aclose()


class Repo:
    def __init__(self, mongo_db: MongoDatabase) -> None:
        self._db = mongo_db

    async def next_model(self, uid: domain.UID) -> tuple[evolve.Model, bool]:
        collection_name = adapter.get_component_name(evolve.Model)
        collection = self._db[collection_name]

        docs = [doc async for doc in collection.find({}, projection=["_id", "day", "llh_mean", "alfa_mean"])]

        docs.sort(key=lambda doc: doc.get("llh_mean", 0), reverse=True)

        for i, doc in enumerate(docs):
            doc["rank"] = i**2

        docs.sort(key=lambda doc: doc.get("alfa_mean", 0), reverse=True)
        target_rank = 0

        for i, doc in enumerate(docs):
            doc["rank"] += i**2

            if doc["_id"] == uid:
                target_rank = doc["rank"]

        ids = []
        rank = docs[0]["rank"]
        day = docs[0]["day"]

        for doc in docs:
            if (doc["day"], -abs(doc["rank"] - target_rank)) == (day, -abs(rank - target_rank)):
                ids.append(doc["_id"])

                continue

            if (doc["day"], -abs(doc["rank"] - target_rank)) < (day, -abs(rank - target_rank)):
                ids = [doc["_id"]]
                rank = doc["rank"]
                day = doc["day"]

        return await self.get(evolve.Model, domain.UID(random.choice(ids))), rank >= target_rank  # noqa: S311

    async def sample_models(self, n: int) -> list[evolve.Model]:
        collection_name = adapter.get_component_name(evolve.Model)
        collection = self._db[collection_name]
        pipeline = [{"$sample": {"size": n}}]

        try:
            return [self._create_entity(evolve.Model, doc) async for doc in await collection.aggregate(pipeline)]
        except PyMongoError as err:
            raise errors.AdapterError("can't sample organisms") from err

    async def count_models(self) -> int:
        collection_name = adapter.get_component_name(evolve.Model)
        collection = self._db[collection_name]

        try:
            return await collection.count_documents({})
        except PyMongoError as err:
            raise errors.AdapterError("can't count organisms") from err

    async def get[E: domain.Entity](
        self,
        t_entity: type[E],
        uid: domain.UID | None = None,
    ) -> E:
        collection_name = adapter.get_component_name(t_entity)
        uid = uid or domain.UID(collection_name)

        if (doc := await self._load(collection_name, uid)) is None:
            doc = await self._create_new(collection_name, uid)

        return self._create_entity(t_entity, doc)

    async def get_all[E: domain.Entity](
        self,
        t_entity: type[E],
    ) -> AsyncIterator[E]:
        collection_name = adapter.get_component_name(t_entity)
        db = self._db[collection_name]

        try:
            async for doc in db.find({}):
                yield self._create_entity(t_entity, doc)
        except PyMongoError as err:
            raise errors.AdapterError("can't load entities from {collection_name}") from err

    async def _load(self, collection_name: str, uid: domain.UID) -> MongoDocument | None:
        collection = self._db[collection_name]

        try:
            return await collection.find_one({_MONGO_ID: uid})
        except PyMongoError as err:
            raise errors.AdapterError("can't load {collection_name}.{uid}") from err

    async def _create_new(self, collection_name: str, uid: domain.UID) -> MongoDocument | None:
        doc = {
            _MONGO_ID: uid,
            VER: 0,
            DAY: datetime.datetime(*consts.START_DAY.timetuple()[:3]),
        }

        collection = self._db[collection_name]

        try:
            await collection.insert_one(doc)
        except PyMongoError as err:
            raise errors.AdapterError("can't create {collection_name}.{uid}") from err

        return doc

    def _create_entity[E: domain.Entity](self, t_entity: type[E], doc: Any) -> E:
        uid = doc.pop(_MONGO_ID)
        doc[REV] = {
            UID: uid,
            VER: doc.pop(VER),
        }

        try:
            return t_entity.model_validate(doc)
        except ValidationError as err:
            collection_name = adapter.get_component_name(t_entity)
            raise errors.AdapterError(f"can't create entity {collection_name}.{uid} {err}") from err

    async def save(self, entity: domain.Entity) -> None:
        collection_name = adapter.get_component_name(entity)

        doc = entity.model_dump()
        doc.pop(REV)

        try:
            updated = await self._db[collection_name].find_one_and_update(
                {_MONGO_ID: entity.uid, VER: entity.ver, DAY: {"$lte": doc[DAY]}},
                {"$inc": {VER: 1}, "$set": doc},
                projection={_MONGO_ID: False},
            )
        except PyMongoError as err:
            raise errors.AdapterError("can't save entities") from err

        if updated is None:  # type: ignore[reportUnnecessaryComparison]
            raise errors.AdapterError(f"wrong version {collection_name}.{entity.uid}")

    async def delete(self, entity: domain.Entity) -> None:
        collection_name = adapter.get_component_name(entity)
        collection = self._db[collection_name]

        try:
            result = await collection.delete_one({_MONGO_ID: entity.uid})
        except PyMongoError as err:
            raise errors.AdapterError("can't delete organisms") from err

        if result.deleted_count != 1:
            raise errors.AdapterError(f"can't delete {collection_name}.{entity.uid}")

    async def drop(self, entity_type: type[domain.Entity]) -> None:
        collection_name = adapter.get_component_name(entity_type)
        collection = self._db[collection_name]

        try:
            await collection.drop()
        except PyMongoError as err:
            raise errors.AdapterError("can't delete {collection_name}") from err
