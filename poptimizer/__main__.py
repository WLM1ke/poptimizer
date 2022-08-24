"""Основная точка входа для запуска приложения."""
from __future__ import annotations

import asyncio
import logging
import signal
import types
from typing import Awaitable, Callable

import aiohttp
from motor.motor_asyncio import AsyncIOMotorClient

from poptimizer.config import Config
from poptimizer.data import updater
from poptimizer.data.repo import Repo
from poptimizer.data.trading_day import DatesSrv


class App:
    """Асинхронное приложение-контекстные менеджер, которое может быть остановлено SIGINT и SIGTERM."""

    def __init__(self, cfg: Config | None = None) -> None:
        """Инициализирует приложение."""
        self._cfg = cfg or Config()
        logging.basicConfig(level=logging.INFO)
        self._logger = logging.getLogger("App")
        self._stop_event = asyncio.Event()
        self._resources: list[Callable[[], None] | Awaitable[None]] = []

    async def __aenter__(self) -> App:
        """Организует перехват системных сигналов для корректного завершения работы."""
        loop = asyncio.get_event_loop()

        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, self._signal_handler)

        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: types.TracebackType | None,
    ) -> None:
        """Логирует выход из контекстного менеджера."""
        count = len(self._resources)
        self._logger.info(f"closing {count} resources")

        for res in reversed(self._resources):
            if isinstance(res, Awaitable):
                await res
                continue

            res()

        self._logger.info("shutdown finished")

    async def run(self) -> None:
        """Запускает приложение."""
        mongo = AsyncIOMotorClient(self._cfg.mongo.uri, tz_aware=False)
        self._resources.append(mongo.close)

        repo = Repo(mongo[self._cfg.mongo.db])

        session = aiohttp.ClientSession(
            connector=aiohttp.TCPConnector(limit=self._cfg.http_client.pool_size),
        )
        self._resources.append(session.close())

        dates_srv = DatesSrv(repo, session)

        await updater.Updater(dates_srv).run(self._stop_event)

    def _signal_handler(self) -> None:
        self._logger.info("shutdown signal received")

        self._stop_event.set()


async def main() -> None:
    """Запускает эволюцию с остановкой по SIGINT и SIGTERM."""
    async with App() as app:
        await app.run()


if __name__ == "__main__":
    asyncio.run(main())
