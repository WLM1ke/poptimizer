"""Основная точка входа для запуска приложения."""
from __future__ import annotations

import asyncio
import logging
import signal
import types
from contextlib import asynccontextmanager
from typing import Final

import aiohttp
import uvloop
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from poptimizer import config, exceptions, lgr, server
from poptimizer.data import data

_HEADERS: Final = types.MappingProxyType({"User-Agent": "POptimizer"})


class App:
    """Асинхронное приложение, которое может быть остановлено SIGINT и SIGTERM."""

    def __init__(self, cfg: config.Config | None = None) -> None:
        self._cfg = cfg or config.Config()
        self._logger = logging.getLogger("App")

    async def run(self) -> None:
        """Запускает приложение."""
        async with (  # noqa: WPS316
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
            stop_event = asyncio.Event()

            tasks = [
                asyncio.create_task(coro)
                for coro in (
                    data.app(mongo, session).run(stop_event),
                    server.create(self._cfg.server.host, self._cfg.server.port).serve(),
                )
            ]

            await self._run_with_graceful_shutdown(tasks, stop_event)

    async def _run_with_graceful_shutdown(
        self,
        tasks: list[asyncio.Task[None]],
        stop_event: asyncio.Event,
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
                signal.raise_signal(signal.SIGINT)
                stop_event.set()

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
