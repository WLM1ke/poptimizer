"""Сервер, показывающий SPA Frontend, и отвечающий на Backend запросы."""
import asyncio
import logging

from aiohttp import web

from poptimizer.data.edit import selected
from poptimizer.server import logger, middleware, views


class Server:
    """Сервер, показывающий SPA Frontend и отвечающий на Backend запросы.

    Реализует протокол сервиса, останавливающегося после завершения события.
    """

    def __init__(
        self,
        host: str,
        port: int,
        selected_srv: selected.Service,
    ):
        self._logger = logging.getLogger("Server")
        self._host = host
        self._port = port

        self._selected_srv = selected_srv

    async def run(self, stop_event: asyncio.Event) -> None:
        """Запускает сервер и останавливает его после завершения события."""
        app = web.Application(middlewares=[middleware.set_start_time_and_headers, middleware.error])

        views.Selected.register(app, self._selected_srv)
        views.Frontend.register(app)

        runner = web.AppRunner(
            app,
            handle_signals=False,
            access_log_class=logger.AccessLogger,
            access_log=self._logger,
        )
        await runner.setup()
        site = web.TCPSite(
            runner,
            self._host,
            self._port,
        )

        await site.start()

        self._logger.info(f"started on http://{self._host}:{self._port}")

        await stop_event.wait()

        await runner.cleanup()

        self._logger.info("stopped")
