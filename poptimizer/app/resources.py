"""Контекстные менеджеры с ресурсами, необходимыми для работы приложения."""
import asyncio
import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator, NamedTuple

import aiohttp
from motor.motor_asyncio import AsyncIOMotorClient

from poptimizer.app import config
from poptimizer.utils import http, lgr, mongo, signals


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
        signals.suppressor(logger) as stop_event,
        http.client(cfg.http_client.con_per_host) as session,
        lgr.config(
            session=session,
            token=cfg.logger.telegram_token,
            chat_id=cfg.logger.telegram_chat_id,
            level=cfg.logger.level,
        ),
        mongo.client(cfg.mongo.uri) as mongo_client,
    ):
        yield Resources(
            logger=logger,
            mongo_client=mongo_client,
            http_session=session,
            stop_event=stop_event,
        )
