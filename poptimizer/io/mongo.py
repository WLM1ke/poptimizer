from collections.abc import AsyncIterator, Mapping
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any, TypeAlias

from motor.core import AgnosticClient
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import MongoDsn

if TYPE_CHECKING:
    MongoClient: TypeAlias = AgnosticClient[Mapping[str, Any]]
else:
    MongoClient: TypeAlias = AgnosticClient


@asynccontextmanager
async def client(uri: MongoDsn) -> AsyncIterator[MongoClient]:
    motor: MongoClient = AsyncIOMotorClient(str(uri), tz_aware=False)
    try:
        yield motor
    finally:
        motor.close()
