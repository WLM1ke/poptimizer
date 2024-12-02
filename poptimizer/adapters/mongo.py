import datetime
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
from poptimizer.domain.evolve import organism

_MONGO_ID: Final = "_id"
_REV: Final = "rev"
_VER: Final = "ver"
_UID: Final = "uid"
_DAY: Final = "day"

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

    async def next_org(self) -> organism.Organism:
        collection_name = adapter.get_component_name(organism.Organism)
        collection = self._db[collection_name]
        pipeline = [
            {
                "$project": {
                    "day": True,
                    "total_alfa": True,
                },
            },
            {"$sort": {"day": pymongo.ASCENDING, "total_alfa": pymongo.ASCENDING}},
            {"$limit": 1},
        ]

        try:
            doc = await anext(await collection.aggregate(pipeline))
        except (PyMongoError, StopAsyncIteration) as err:
            raise errors.AdapterError("can't load next organism") from err

        return await self.get(organism.Organism, domain.UID(doc["_id"]))

    async def sample_orgs(self, n: int) -> list[organism.Organism]:
        collection_name = adapter.get_component_name(organism.Organism)
        collection = self._db[collection_name]
        pipeline = [{"$sample": {"size": n}}]

        try:
            return [self._create_entity(organism.Organism, doc) async for doc in await collection.aggregate(pipeline)]
        except PyMongoError as err:
            raise errors.AdapterError("can't sample organisms") from err

    async def count_orgs(self) -> int:
        collection_name = adapter.get_component_name(organism.Organism)
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

    async def _load(self, collection_name: str, uid: domain.UID) -> MongoDocument | None:
        collection = self._db[collection_name]

        try:
            return await collection.find_one({_MONGO_ID: uid})
        except PyMongoError as err:
            raise errors.AdapterError("can't load {collection_name}.{uid}") from err

    async def _create_new(self, collection_name: str, uid: domain.UID) -> MongoDocument | None:
        doc = {
            _MONGO_ID: uid,
            _VER: 0,
            _DAY: datetime.datetime(*consts.START_DAY.timetuple()[:3]),
        }

        collection = self._db[collection_name]

        try:
            await collection.insert_one(doc)
        except PyMongoError as err:
            raise errors.AdapterError("can't create {collection_name}.{uid}") from err

        return doc

    def _create_entity[E: domain.Entity](self, t_entity: type[E], doc: Any) -> E:
        uid = doc.pop(_MONGO_ID)
        doc[_REV] = {
            _UID: uid,
            _VER: doc.pop(_VER),
        }

        try:
            return t_entity.model_validate(doc)
        except ValidationError as err:
            collection_name = adapter.get_component_name(t_entity)
            raise errors.AdapterError(f"can't create entity {collection_name}.{uid}") from err

    async def save(self, entity: domain.Entity) -> None:
        collection_name = adapter.get_component_name(entity)

        doc = entity.model_dump()
        doc.pop(_REV)

        try:
            updated = await self._db[collection_name].find_one_and_update(
                {_MONGO_ID: entity.uid, _VER: entity.ver, _DAY: {"$lte": doc[_DAY]}},
                {"$inc": {_VER: 1}, "$set": doc},
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
            raise errors.AdapterError("can't sample organisms") from err

        if result.deleted_count != 1:
            raise errors.AdapterError(f"can't delete {collection_name}.{entity.uid}")

    async def delete_all[E: domain.Entity](self, t_entity: type[E]) -> None:
        collection_name = adapter.get_component_name(t_entity)

        try:
            await self._db.drop_collection(collection_name)
        except PyMongoError as err:
            raise errors.AdapterError("can't drop {collection_name}") from err
