"""Основная точка входа для запуска приложения."""
import asyncio
from typing import Protocol

import uvloop

from poptimizer.app import config, resources, server, updater
from poptimizer.core import exceptions


class Module(Protocol):
    """Независимый модуль программы."""

    async def run(self, stop_event: asyncio.Event) -> None:
        """Запускает независимый модуль и останавливает его после завершения события."""


async def run_app() -> None:
    """Запускает асинхронное приложение, которое может быть остановлено SIGINT и SIGTERM."""
    async with resources.acquire(config.Resources()) as res:
        res.logger.info("starting...")

        modules: list[Module] = [
            updater.create(
                res.mongo_client,
                res.http_session,
            ),
            server.create(
                config.Server(),
                res.mongo_client,
            ),
        ]
        tasks = [asyncio.create_task(module.run(res.stop_event)) for module in modules]

        for task in asyncio.as_completed(tasks):
            try:
                await task
            except exceptions.POError as err:
                res.logger.exception(f"abnormal termination -> {err}")
            except BaseException as err:  # noqa: WPS424
                err_text = repr(err)

                res.logger.exception(f"abnormal termination with uncaught error -> {err_text}")
            finally:
                res.stop_event.set()


def main() -> None:
    """Запускает эволюцию с остановкой по SIGINT и SIGTERM."""
    uvloop.install()
    asyncio.run(run_app())


if __name__ == "__main__":
    main()
