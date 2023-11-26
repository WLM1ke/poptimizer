from __future__ import annotations

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any

from motor.motor_asyncio import AsyncIOMotorClient

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Mapping

    from motor.core import AgnosticClient, AgnosticCollection, AgnosticDatabase
    from pydantic import MongoDsn

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
