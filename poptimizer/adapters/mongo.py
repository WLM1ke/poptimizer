import random
from collections.abc import AsyncGenerator, AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Final

import pymongo
from bson.errors import BSONError
from pydantic import MongoDsn, ValidationError
from pymongo.asynchronous import collection, database
from pymongo.errors import PyMongoError

from poptimizer.core import domain, errors
from poptimizer.evolve.evolution import evolve
from poptimizer.fsm import uow

_MONGO_ID: Final = "_id"
_VER: Final = "ver"
_UID: Final = "uid"

type MongoDocument = dict[str, Any]
type MongoClient = pymongo.AsyncMongoClient[MongoDocument]
type MongoDatabase = database.AsyncDatabase[MongoDocument]
type MongoCollection = collection.AsyncCollection[MongoDocument]


@asynccontextmanager
async def _wrap_err(msg: str) -> AsyncGenerator[None]:
    try:
        yield
    except (PyMongoError, BSONError) as err:
        raise errors.AdapterError(msg) from err


@asynccontextmanager
async def db(uri: MongoDsn, db: str) -> AsyncGenerator[MongoDatabase]:
    mongo_client: MongoClient = pymongo.AsyncMongoClient(str(uri), tz_aware=False)
    try:
        yield mongo_client[db]
    finally:
        await mongo_client.aclose()


class Repo:
    def __init__(self, mongo_db: MongoDatabase) -> None:
        self._db = mongo_db

    async def next_model_for_update(self) -> tuple[evolve.Model, uow.Version]:
        collection_name = evolve.Model.__name__
        collection = self._db[collection_name]

        async with _wrap_err("can't get next model"):
            doc = await collection.find_one(
                sort=[
                    ("day", pymongo.ASCENDING),
                    ("llh", pymongo.DESCENDING),
                ],
            )

            return self._create_obj(evolve.Model, doc)

    async def delete_worst_model(self) -> None:
        collection_name = evolve.Model.__name__
        collection = self._db[collection_name]

        async with _wrap_err("can't get next model"):
            await collection.find_one_and_delete(
                {},
                sort=random.choice(  # noqa: S311
                    [
                        [("alfa", pymongo.ASCENDING)],
                        [("llh", pymongo.ASCENDING)],
                        [("day", pymongo.ASCENDING), ("duration", pymongo.DESCENDING)],
                    ]
                ),
            )

    async def get_models(self, day: domain.Day) -> list[evolve.Model]:
        collection_name = evolve.Model.__name__
        collection = self._db[collection_name]

        dt = datetime(day.year, day.month, day.day)

        async with _wrap_err("can't get models"):
            return [self._create_obj(evolve.Model, doc)[0] async for doc in collection.find({"day": dt})]

    async def sample_models(self, n: int) -> list[evolve.Model]:
        collection_name = evolve.Model.__name__
        collection = self._db[collection_name]
        pipeline = [{"$sample": {"size": n}}]

        async with _wrap_err("can't sample model"):
            return [self._create_obj(evolve.Model, doc)[0] async for doc in await collection.aggregate(pipeline)]

    async def count_models(self) -> int:
        collection_name = evolve.Model.__name__
        collection = self._db[collection_name]

        async with _wrap_err("can't count models"):
            return await collection.count_documents({})

    async def get[E: domain.Object](
        self,
        t_obj: type[E],
        uid: domain.UID,
    ) -> tuple[E, uow.Version]:
        collection_name = t_obj.__name__

        doc = await self._load_or_create(collection_name, uid)

        return self._create_obj(t_obj, doc)

    async def get_all[E: domain.Object](
        self,
        t_obj: type[E],
    ) -> AsyncIterator[E]:
        collection_name = t_obj.__name__
        db = self._db[collection_name]

        async with _wrap_err(f"can't load entities from {collection_name}"):
            async for doc in db.find({}):
                obj, _ = self._create_obj(t_obj, doc)

                yield obj

    async def _load_or_create(self, collection_name: str, uid: domain.UID) -> MongoDocument | None:
        collection = self._db[collection_name]

        async with _wrap_err(f"can't load {collection_name}.{uid}"):
            return await collection.find_one_and_update(
                {_MONGO_ID: uid},
                {
                    "$setOnInsert": {
                        _VER: 0,
                    },
                },
                upsert=True,
                return_document=pymongo.ReturnDocument.AFTER,
            )

    def _create_obj[E: domain.Object](self, t_obj: type[E], doc: Any) -> tuple[E, uow.Version]:
        doc |= {_UID: doc[_MONGO_ID]}
        try:
            return t_obj.model_validate(doc), uow.Version(doc[_VER])
        except ValidationError as err:
            collection_name = t_obj.__name__
            uid = doc.get(_UID)

            raise errors.AdapterError(f"can't create {collection_name}.{uid} {err}") from err

    async def save(self, obj: domain.Object, ver: uow.Version) -> None:
        collection_name = obj.__class__.__name__

        doc = obj.model_dump(exclude={_UID})
        doc[_MONGO_ID] = obj.uid
        doc[_VER] = ver + 1

        async with _wrap_err("can't save entities"):
            replaced = await self._db[collection_name].find_one_and_replace(
                {_MONGO_ID: obj.uid, _VER: ver},
                doc,
            )

        if replaced is None:
            raise errors.AdapterError(f"wrong version {collection_name}.{obj.uid}")

    async def delete(self, obj: domain.Object) -> None:
        collection_name = obj.__class__.__name__
        collection = self._db[collection_name]

        async with _wrap_err("can't delete entity"):
            result = await collection.delete_one({_MONGO_ID: obj.uid})

        if result.deleted_count != 1:
            raise errors.AdapterError(f"can't delete {collection_name}.{obj.uid}")

    async def drop(self, obj_type: type[domain.Object]) -> None:
        collection_name = obj_type.__name__
        collection = self._db[collection_name]

        async with _wrap_err(f"can't delete {collection_name}"):
            await collection.drop()
