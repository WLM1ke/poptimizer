import datetime
from collections.abc import AsyncIterator, Iterable, Mapping
from contextlib import asynccontextmanager
from typing import Any, Final

from motor.core import AgnosticClient, AgnosticCollection, AgnosticDatabase
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import MongoDsn, ValidationError
from pymongo.errors import PyMongoError

from poptimizer.adapter import adapter
from poptimizer.domain import consts
from poptimizer.domain.entity import entity

type MongoDocument = Mapping[str, Any]
type MongoClient = AgnosticClient[MongoDocument]
type MongoDatabase = AgnosticDatabase[MongoDocument]
type MongoCollection = AgnosticCollection[MongoDocument]


_MONGO_ID: Final = "_id"
_REV: Final = "rev"
_VER: Final = "ver"
_UID: Final = "uid"
_DAY: Final = "day"


@asynccontextmanager
async def client(uri: MongoDsn) -> AsyncIterator[MongoClient]:
    motor: MongoClient = AsyncIOMotorClient(str(uri), tz_aware=False)
    try:
        yield motor
    finally:
        motor.close()


class Repo:
    def __init__(self, db: MongoDatabase) -> None:
        self._db = db

    async def get[E: entity.Entity](
        self,
        t_entity: type[E],
        uid: entity.UID | None = None,
    ) -> E:
        collection_name = adapter.get_component_name(t_entity)
        uid = uid or entity.UID(collection_name)

        if (doc := await self._load(collection_name, uid)) is None:
            doc = await self._create_new(collection_name, uid)

        return self._create_entity(t_entity, doc)

    async def _load(self, collection_name: str, uid: entity.UID) -> MongoDocument | None:
        collection: MongoCollection = self._db[collection_name]
        try:
            return await collection.find_one({_MONGO_ID: uid})
        except PyMongoError as err:
            raise adapter.AdaptersError("can't load {collection_name}.{uid}") from err

    async def _create_new(self, collection_name: str, uid: entity.UID) -> MongoDocument | None:
        doc = {
            _MONGO_ID: uid,
            _VER: 0,
            _DAY: datetime.datetime(*consts.START_DAY.timetuple()[:3]),
        }

        collection: MongoCollection = self._db[collection_name]

        try:
            await collection.insert_one(doc)
        except PyMongoError as err:
            raise adapter.AdaptersError("can't create {collection_name}.{uid}") from err

        return doc

    def _create_entity[E: entity.Entity](self, t_entity: type[E], doc: Any) -> E:
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

    async def save(self, entities: Iterable[entity.Entity]) -> None:
        try:
            async with (
                await self._db.client.start_session() as session,  # type: ignore[reportUnknownMemberType]
                session.start_transaction(),
            ):
                for entity in entities:
                    doc = entity.model_dump()
                    doc.pop(_REV)

                    collection_name = adapter.get_component_name(entity)
                    if (
                        await self._db[collection_name].find_one_and_update(
                            {_MONGO_ID: entity.uid, _VER: entity.ver, _DAY: {"$lte": doc[_DAY]}},
                            {"$inc": {_VER: 1}, "$set": doc},
                            projection={_MONGO_ID: False},
                            session=session,
                        )
                        is None
                    ):  # type: ignore[reportUnnecessaryComparison]
                        raise adapter.AdaptersError(f"wrong version {collection_name}.{entity.uid}")
        except PyMongoError as err:
            raise adapter.AdaptersError("can't save entities") from err
