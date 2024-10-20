import datetime
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any, Final

import pymongo
from pydantic import MongoDsn, ValidationError
from pymongo import errors

from poptimizer.adapter import adapter
from poptimizer.domain import consts, domain

_MONGO_ID: Final = "_id"
_REV: Final = "rev"
_VER: Final = "ver"
_UID: Final = "uid"
_DAY: Final = "day"

type MongoDocument = dict[str, Any]
type MongoClient = pymongo.AsyncMongoClient[MongoDocument]


@asynccontextmanager
async def client(uri: MongoDsn) -> AsyncIterator[MongoClient]:
    mongo_client: MongoClient = pymongo.AsyncMongoClient(str(uri), tz_aware=False)
    try:
        yield mongo_client
    finally:
        await mongo_client.aclose()


class Repo:
    def __init__(self, mongo_client: MongoClient, db: str) -> None:
        self._db = mongo_client[db]

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
        except errors.PyMongoError as err:
            raise adapter.AdaptersError("can't load {collection_name}.{uid}") from err

    async def _create_new(self, collection_name: str, uid: domain.UID) -> MongoDocument | None:
        doc = {
            _MONGO_ID: uid,
            _VER: 0,
            _DAY: datetime.datetime(*consts.START_DAY.timetuple()[:3]),
        }

        collection = self._db[collection_name]

        try:
            await collection.insert_one(doc)
        except errors.PyMongoError as err:
            raise adapter.AdaptersError("can't create {collection_name}.{uid}") from err

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
            raise adapter.AdaptersError(f"can't create entity {collection_name}.{uid}") from err

    async def save(self, entity: domain.Entity) -> None:
        collection_name = adapter.get_component_name(domain)

        doc = entity.model_dump()
        doc.pop(_REV)

        try:
            updated = await self._db[collection_name].find_one_and_update(
                {_MONGO_ID: entity.uid, _VER: entity.ver, _DAY: {"$lte": entity.day}},
                {"$inc": {_VER: 1}, "$set": doc},
                projection={_MONGO_ID: False},
            )
        except errors.PyMongoError as err:
            raise adapter.AdaptersError("can't save entities") from err

        if updated is None:  # type: ignore[reportUnnecessaryComparison]
            raise adapter.AdaptersError(f"wrong version {collection_name}.{entity.uid}")
