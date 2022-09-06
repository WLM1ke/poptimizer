"""Сервер, показывающий SPA Frontend, и отвечающий на Backend запросы."""
import asyncio
import logging

from aiohttp import web

from poptimizer.server import frontend, logger


class Server:
    """Сервер, показывающий SPA Frontend и отвечающий на Backend запросы.

    Реализует протокол сервиса, останавливающегося после завершения события.
    """

    def __init__(self, host: str, port: int):
        self._host = host
        self._port = port

    async def run(self, stop_event: asyncio.Event) -> None:
        """Запускает сервер и останавливает его после завершения события."""
        app = web.Application(middlewares=[logger.set_start_time_and_headers])
        frontend.add(app)

        runner = web.AppRunner(
            app,
            handle_signals=False,
            access_log_class=logger.AccessLogger,
            access_log=logging.getLogger("Server"),
        )
        await runner.setup()
        site = web.TCPSite(
            runner,
            self._host,
            self._port,
        )

        await site.start()

        await stop_event.wait()

        await runner.cleanup()
