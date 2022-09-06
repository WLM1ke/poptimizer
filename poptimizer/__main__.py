"""Основная точка входа для запуска приложения."""
from __future__ import annotations

import asyncio
import logging
import signal
import types
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator, Final, Protocol

import aiohttp
import uvloop
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from poptimizer import config, exceptions, lgr
from poptimizer.data import data
from poptimizer.server import server

_HEADERS: Final = types.MappingProxyType({"User-Agent": "POptimizer"})
_STATIC: Final = Path(__file__).parents[1] / "static"


class Service(Protocol):
    """Независимый модуль программы."""

    async def run(self, stop_event: asyncio.Event) -> None:
        """Запускает независимый модуль и останавливает его после завершения события."""


class App:
    """Асинхронное приложение, которое может быть остановлено SIGINT и SIGTERM."""

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
            services: list[Service] = [
                data.app(mongo, session),
                server.Server(self._cfg.server.host, self._cfg.server.port),
            ]

            tasks = [asyncio.create_task(service.run(self._stop_event)) for service in services]

            await self._run_with_graceful_shutdown(tasks)

    async def _run_with_graceful_shutdown(
        self,
        tasks: list[asyncio.Task[None]],
    ) -> None:
        """При завершении одной из задач, инициирует graceful shutdown остальных.

        Сервер останавливается по сигналу SIGINT, а остальные службы с помощью события.
        """
        for task in asyncio.as_completed(tasks):
            try:
                await task
            except exceptions.POError as err:
                self._logger.exception(f"abnormal termination {err}")
            except BaseException as err:  # noqa: WPS424
                err_text = repr(err)

                self._logger.exception(f"abnormal termination with uncaught error -> {err_text}")
            finally:
                self._stop_event.set()

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
    async def _motor_collection(self) -> AsyncIOMotorDatabase:
        motor = AsyncIOMotorClient(self._cfg.mongo.uri, tz_aware=False)
        try:
            yield motor[self._cfg.mongo.db]
        finally:
            motor.close()


def main() -> None:
    """Запускает эволюцию с остановкой по SIGINT и SIGTERM."""
    uvloop.install()
    asyncio.run(App().run())


if __name__ == "__main__":
    main()
