"""Контекстный менеджер создающий клиента MongoDB и завершающий его работу."""
from contextlib import asynccontextmanager
from typing import AsyncIterator

from motor.motor_asyncio import AsyncIOMotorClient


@asynccontextmanager
async def client(uri: str) -> AsyncIterator[AsyncIOMotorClient]:
    """Контекстный менеджер создающий клиента MongoDB и завершающий его работу."""
    motor = AsyncIOMotorClient(uri, tz_aware=False)
    try:
        yield motor
    finally:
        motor.close()
