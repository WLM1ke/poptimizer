"""Различные контекстные менеджеры с ресурсами, необходимыми для работы приложения."""
import asyncio
import logging
import signal
import types
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Final

import aiohttp
from motor.motor_asyncio import AsyncIOMotorClient

_SIGNALS: Final = (signal.SIGINT, signal.SIGTERM)
_HEADERS: Final = types.MappingProxyType(
    {
        "User-Agent": "POptimizer",
        "Connection": "keep-alive",
    },
)


@asynccontextmanager
async def signal_suppressor(logger: logging.Logger) -> AsyncGenerator[asyncio.Event, None]:
    """Подавляет действие системных сигналов SIGINT и SIGTERM для asyncio.loop.

    При поступлении системных сигналов устанавливает событие, чтобы асинхронные функции могли отреагировать на это
    корректным завершением.
    """
    loop = asyncio.get_event_loop()

    stop_event = asyncio.Event()

    for add_sig in _SIGNALS:
        loop.add_signal_handler(add_sig, _signal_handler, logger, stop_event)

    try:
        yield stop_event
    finally:

        for remove_sig in _SIGNALS:
            loop.remove_signal_handler(remove_sig)

        logger.info("shutdown completed")


def _signal_handler(logger: logging.Logger, stop_event: asyncio.Event) -> None:
    logger.info("shutdown signal received...")
    stop_event.set()


def http_client(con_per_host: int) -> aiohttp.ClientSession:
    """Создает http-клиент с ограничением количества соединений на хост."""
    return aiohttp.ClientSession(
        connector=aiohttp.TCPConnector(limit_per_host=con_per_host),
        headers=_HEADERS,
    )


@asynccontextmanager
async def mongo_client(uri: str) -> AsyncIOMotorClient:
    """Контекстный менеджер создающий клиента MongoDB и завершающий его работу."""
    motor = AsyncIOMotorClient(uri, tz_aware=False)
    try:
        yield motor
    finally:
        motor.close()
