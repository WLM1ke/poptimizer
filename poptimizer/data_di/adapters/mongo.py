"""Фабрика асинхронного соединения с MongoDB."""
from motor import motor_asyncio


def client_factory(uri: str) -> motor_asyncio.AsyncIOMotorClient:
    """Асинхронный клиент для работы с MongoDB."""
    return motor_asyncio.AsyncIOMotorClient(uri, tz_aware=False)
