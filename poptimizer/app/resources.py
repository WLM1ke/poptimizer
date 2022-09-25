"""Контекстные менеджеры с ресурсами, необходимыми для работы приложения."""
import asyncio
import logging
import signal
import types
from contextlib import asynccontextmanager
from typing import AsyncIterator, Final, NamedTuple

import aiohttp
from motor.motor_asyncio import AsyncIOMotorClient

from poptimizer.app import config, lgr

_SIGNALS: Final = (signal.SIGINT, signal.SIGTERM)
_HEADERS: Final = types.MappingProxyType(
    {
        "User-Agent": "POptimizer",
        "Connection": "keep-alive",
    },
)


@asynccontextmanager
async def signal_suppressor(logger: logging.Logger) -> AsyncIterator[asyncio.Event]:
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


@asynccontextmanager
async def mongo_client(uri: str) -> AsyncIterator[AsyncIOMotorClient]:
    """Контекстный менеджер создающий клиента MongoDB и завершающий его работу."""
    motor = AsyncIOMotorClient(uri, tz_aware=False)
    try:
        yield motor
    finally:
        motor.close()


class Resources(NamedTuple):
    """Ресурсы, необходимые для запуска приложения."""

    logger: logging.Logger
    mongo_client: AsyncIOMotorClient
    http_session: aiohttp.ClientSession
    stop_event: asyncio.Event


@asynccontextmanager
async def acquire(cfg: config.Resources) -> AsyncIterator[Resources]:
    """Контекстный менеджер, инициализирующий ресурсы необходимые для запуска приложения."""
    logger = logging.getLogger(cfg.logger.app_name)

    async with (  # noqa:  WPS316
        signal_suppressor(logger) as stop_event,
        aiohttp.ClientSession(
            connector=aiohttp.TCPConnector(limit_per_host=cfg.http_client.con_per_host),
            headers=_HEADERS,
        ) as session,
        lgr.config(
            session=session,
            token=cfg.logger.telegram_token,
            chat_id=cfg.logger.telegram_chat_id,
            level=cfg.logger.level,
        ),
        mongo_client(cfg.mongo.uri) as mongo,
    ):
        yield Resources(
            logger=logger,
            mongo_client=mongo,
            http_session=session,
            stop_event=stop_event,
        )
