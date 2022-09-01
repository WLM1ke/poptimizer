"""Основная точка входа для запуска приложения."""
from __future__ import annotations

import asyncio
import logging
import signal
import types
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Final

import aiohttp
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection

from poptimizer import config, exceptions, lgr
from poptimizer.data.main import data_app

_HEADERS: Final = types.MappingProxyType({"User-Agent": "POptimizer"})


class App:
    """Асинхронное приложение-контекстные менеджер, которое может быть остановлено SIGINT и SIGTERM."""

    def __init__(self, cfg: config.Config | None = None) -> None:
        self._cfg = cfg or config.Config()
        self._logger = logging.getLogger("App")
        self._stop_event = asyncio.Event()

    async def run(self) -> None:
        """Запускает приложение."""
        async with (  # noqa: WPS316
            self._signal_suppressor(),
            aiohttp.ClientSession(
                connector=aiohttp.TCPConnector(limit=self._cfg.http_client.pool_size),
                headers=_HEADERS,
            ) as session,
            lgr.config(
                session=session,
                token=self._cfg.telegram.token,
                chat_id=self._cfg.telegram.chat_id,
            ),
            self._motor_collection() as mongo,
        ):
            try:
                await data_app(mongo, session).run(self._stop_event)
            except exceptions.POError as err:
                self._logger.critical(f"abnormal termination {err}")

                raise
            except BaseException as err:  # noqa: WPS424
                err_text = repr(err)

                self._logger.critical(f"abnormal termination with uncaught error -> {err_text}")

                raise

    @asynccontextmanager
    async def _signal_suppressor(self) -> AsyncGenerator[None, None]:
        loop = asyncio.get_event_loop()

        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, self._signal_handler)

        try:
            yield
        finally:
            self._logger.info("shutdown completed")

    def _signal_handler(self) -> None:
        self._logger.info("shutdown signal received")

        self._stop_event.set()

    @asynccontextmanager
    async def _motor_collection(self) -> AsyncIOMotorCollection:
        motor = AsyncIOMotorClient(self._cfg.mongo.uri, tz_aware=False)
        try:
            yield motor[self._cfg.mongo.db]
        finally:
            motor.close()


async def main() -> None:
    """Запускает эволюцию с остановкой по SIGINT и SIGTERM."""
    await App().run()


if __name__ == "__main__":
    asyncio.run(main())
