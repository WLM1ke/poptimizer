from collections.abc import AsyncIterator, Mapping
from contextlib import asynccontextmanager
from typing import Any, TypeVar

from motor.core import AgnosticClient
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import MongoDsn

DocumentType = TypeVar("DocumentType", bound=Mapping[str, Any])


@asynccontextmanager
async def client(uri: MongoDsn) -> AsyncIterator[AgnosticClient[DocumentType]]:
    motor: AgnosticClient[DocumentType] = AsyncIOMotorClient(str(uri), tz_aware=False)
    try:
        yield motor
    finally:
        motor.close()
