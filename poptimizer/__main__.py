"""Основная точка входа для запуска приложения."""
import asyncio
import logging
from typing import Protocol

import aiohttp
import uvloop
from motor.motor_asyncio import AsyncIOMotorClient

from poptimizer import config
from poptimizer.core import exceptions
from poptimizer.data import data
from poptimizer.server import server
from poptimizer.shared import ctx, lgr


class Module(Protocol):
    """Независимый модуль программы."""

    async def run(self, stop_event: asyncio.Event) -> None:
        """Запускает независимый модуль и останавливает его после завершения события."""


class App:
    """Асинхронное приложение, которое может быть остановлено SIGINT и SIGTERM."""

    def __init__(self, cfg: config.Config | None = None) -> None:
        self._cfg = cfg or config.Config()
        self._logger = logging.getLogger("App")

    async def run(self) -> None:
        """Запускает приложение."""
        async with (  # noqa: WPS316
            ctx.signal_suppressor(self._logger) as stop_event,
            ctx.http_client(self._cfg.http_client.con_per_host) as session,
            lgr.config(
                session=session,
                token=self._cfg.telegram.token,
                chat_id=self._cfg.telegram.chat_id,
            ),
            ctx.mongo_client(self._cfg.mongo.uri) as mongo_client,
        ):
            await self._run_with_graceful_shutdown(mongo_client, session, stop_event)

    async def _run_with_graceful_shutdown(
        self,
        mongo_client: AsyncIOMotorClient,
        session: aiohttp.ClientSession,
        stop_event: asyncio.Event,
    ) -> None:
        self._logger.info("starting...")

        modules: list[Module] = [
            data.create_app(
                mongo_client,
                session,
            ),
            server.create_server(
                self._cfg.server.host,
                self._cfg.server.port,
                mongo_client,
            ),
        ]
        tasks = [asyncio.create_task(module.run(stop_event)) for module in modules]

        for task in asyncio.as_completed(tasks):
            try:
                await task
            except exceptions.POError as err:
                self._logger.exception(f"abnormal termination -> {err}")
            except BaseException as err:  # noqa: WPS424
                err_text = repr(err)

                self._logger.exception(f"abnormal termination with uncaught error -> {err_text}")
            finally:
                stop_event.set()


def main() -> None:
    """Запускает эволюцию с остановкой по SIGINT и SIGTERM."""
    uvloop.install()
    asyncio.run(App().run())


if __name__ == "__main__":
    main()
