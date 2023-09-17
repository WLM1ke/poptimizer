from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from motor.motor_asyncio import AsyncIOMotorClient


@asynccontextmanager
async def client(uri: str) -> AsyncIterator[AsyncIOMotorClient]:
    motor = AsyncIOMotorClient(str(uri), tz_aware=False)
    try:
        yield motor
    finally:
        motor.close()
