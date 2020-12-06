"""Общие соединения http и MongoDB."""
import typing

from motor import motor_asyncio

# Асинхронный клиент для MongoDB
_MONGO_URI = "mongodb://localhost:27017"
MONGO_CLIENT: typing.Final = motor_asyncio.AsyncIOMotorClient(_MONGO_URI, tz_aware=False)
