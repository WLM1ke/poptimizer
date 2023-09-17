import asyncio
import datetime
from collections.abc import Iterator
from types import TracebackType
from typing import Any, Final, Self, TypeVar

from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import ValidationError
from pymongo.errors import PyMongoError

from poptimizer.core import domain, errors

_MONGO_ID: Final = "_id"
_REV: Final = "rev"
_VER: Final = "ver"
_UID: Final = "uid"
_TIMESTAMP: Final = "timestamp"


TEntity = TypeVar("TEntity", bound=domain.BaseEntity)


class IdentityMap:
    def __init__(self, error_type: type[errors.POError]) -> None:
        self._error_type = error_type
        self._seen: dict[tuple[type, str], tuple[domain.BaseEntity, bool]] = {}
        self._lock = asyncio.Lock()

    def __iter__(self) -> Iterator[domain.BaseEntity]:
        yield from [model for model, for_update in self._seen.values() if for_update]

    async def __aenter__(self) -> Self:
        await self._lock.acquire()

        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool:
        self._lock.release()

        return False

    def get(
        self,
        t_entity: type[TEntity],
        uid: str,
        *,
        for_update: bool,
    ) -> TEntity | None:
        entity, update_flag = self._seen.get((t_entity, uid), (None, False))
        if entity is None:
            return None

        if not isinstance(entity, t_entity):
            raise self._error_type(f"can't load form identity map {t_entity}({uid})")

        self.save(entity, for_update=update_flag or for_update)

        return entity

    def save(self, entity: TEntity, *, for_update: bool) -> None:
        self._seen[entity.__class__, entity.uid] = (entity, for_update)


def _collection_name(t_entity: type[TEntity]) -> str:
    return t_entity.__qualname__.lower()


class MongoUOW:
    def __init__(
        self,
        mongo_client: AsyncIOMotorClient,
        db: str,
        error_type: type[errors.POError],
    ) -> None:
        self._mongo_client = mongo_client
        self._db = db
        self._error_type = error_type
        self._identity_map = IdentityMap(error_type)

    async def get(self, t_entity: type[TEntity], uid: str | None, *, for_update: bool = True) -> TEntity:
        collection_name = _collection_name(t_entity)
        uid = uid or collection_name

        async with self._identity_map as identity_map:
            if loaded := identity_map.get(t_entity, uid, for_update=for_update):
                return loaded

            if (doc := await self._load(collection_name, uid)) is None:
                doc = await self._create_new(collection_name, uid)

            entity = self._create_entity(t_entity, doc)

            identity_map.save(entity, for_update=for_update)

        return entity

    async def _load(self, collection_name: str, uid: str) -> Any:
        collection = self._mongo_client[self._db][collection_name]
        try:
            return await collection.find_one({_MONGO_ID: uid})
        except PyMongoError as err:
            raise self._error_type("can't load {collection_name}.{uid}") from err

    async def _create_new(self, collection_name: str, uid: str) -> Any:
        doc = {
            _MONGO_ID: uid,
            _VER: 0,
            _TIMESTAMP: datetime.datetime(datetime.MINYEAR, 1, 1),
        }

        collection = self._mongo_client[self._db][collection_name]

        try:
            await collection.insert_one(doc)
        except PyMongoError as err:
            raise self._error_type("can't create {collection_name}.{uid}") from err

        return doc

    def _create_entity(self, t_entity: type[TEntity], doc: Any) -> TEntity:
        doc[_REV] = {
            _UID: doc.pop(_MONGO_ID),
            _VER: doc.pop(_VER),
        }

        try:
            return t_entity.model_validate(doc)
        except ValidationError as err:
            raise self._error_type("can't load {collection_name}.{uid}") from err

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool:
        if exc_value is not None:
            return False

        await self._commit()

        return True

    async def _commit(self) -> None:
        async with (
            await self._mongo_client.start_session() as session,
            session.start_transaction(),
        ):
            db = session.client[self._db]
            for entity in self._identity_map:
                doc = entity.model_dump()
                doc.pop(_REV)

                collection_name = _collection_name(entity.__class__)
                rez = await db[collection_name].find_one_and_update(
                    {_MONGO_ID: entity.uid, _VER: entity.ver},
                    {"$inc": {_VER: 1}, "$set": doc},
                    projection={_MONGO_ID: False},
                    session=session,
                )
                if rez is None:
                    raise self._error_type(f"wrong version {collection_name}.{entity.uid}")
