from collections.abc import AsyncIterator, Mapping
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any

from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import MongoDsn

if TYPE_CHECKING:
    from motor.core import AgnosticClient, AgnosticCollection, AgnosticDatabase

type MongoDocument = Mapping[str, Any]
type MongoClient = AgnosticClient[MongoDocument]
type MongoDatabase = AgnosticDatabase[MongoDocument]
type MongoCollection = AgnosticCollection[MongoDocument]


@asynccontextmanager
async def client(uri: MongoDsn) -> AsyncIterator[MongoClient]:
    motor: MongoClient = AsyncIOMotorClient(str(uri), tz_aware=False)
    try:
        yield motor
    finally:
        motor.close()
