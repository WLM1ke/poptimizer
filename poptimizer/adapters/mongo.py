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

        projection = ["_id", "day", "llh_mean", "alfa_mean"]
        docs = [doc async for doc in collection.find({}, projection=projection)]

        key_count = len(projection)
        target: MongoDocument | None = None
        min_day = docs[0]["day"]

        for doc in docs:
            if len(doc) != key_count:
                return await self.get(evolve.Model, domain.UID(doc["_id"])), True

            if doc["_id"] == uid:
                target = doc

            min_day = min(min_day, doc["day"])

        if target is None:
            return await self.get(evolve.Model, domain.UID(random.choice(docs)["_id"])), False  # noqa: S311

        docs = [doc for doc in docs if doc["day"] == min_day]

        if len(docs) == 1:
            return await self.get(evolve.Model, domain.UID(docs[0]["_id"])), False

        return await self._farthest_from_target(docs, target)

    async def _farthest_from_target(
        self,
        docs: list[MongoDocument],
        target: MongoDocument,
    ) -> tuple[evolve.Model, bool]:
        min_llh = docs[0]
        max_llh = docs[0]
        min_alfa = docs[0]
        max_alfa = docs[0]

        for doc in docs:
            if doc["llh_mean"] < min_llh["llh_mean"]:
                min_llh = doc

            if doc["llh_mean"] > max_llh["llh_mean"]:
                max_llh = doc

            if doc["alfa_mean"] < min_alfa["alfa_mean"]:
                min_alfa = doc

            if doc["alfa_mean"] > max_alfa["alfa_mean"]:
                max_alfa = doc

        selected = max(
            (
                min_llh,
                False,
                (target["llh_mean"] - min_llh["llh_mean"]) / (max_llh["llh_mean"] - min_llh["llh_mean"]),
            ),
            (
                max_llh,
                True,
                (max_llh["llh_mean"] - target["llh_mean"]) / (max_llh["llh_mean"] - min_llh["llh_mean"]),
            ),
            (
                min_alfa,
                False,
                (target["alfa_mean"] - min_alfa["alfa_mean"]) / (max_alfa["alfa_mean"] - min_alfa["alfa_mean"]),
            ),
            (
                max_alfa,
                True,
                (max_alfa["alfa_mean"] - target["alfa_mean"]) / (max_alfa["alfa_mean"] - min_alfa["alfa_mean"]),
            ),
            key=lambda x: x[2],
        )

        return await self.get(evolve.Model, domain.UID(selected[0]["_id"])), selected[1]

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
