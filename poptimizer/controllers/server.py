import asyncio
from collections.abc import Callable

from aiohttp import web
from pydantic import HttpUrl

from poptimizer.controllers import middleware, portfolio
from poptimizer.core import domain


class ServerStatusChanged(domain.Event):
    status: str


class Server:
    def __init__(
        self,
        url: HttpUrl,
        requester: middleware.Requester,
    ) -> None:
        self._url = url
        self._requester = requester

    async def publish(self, bus: Callable[[domain.Event], None]) -> None:
        app = self._prepare_app()

        runner = web.AppRunner(
            app,
            handle_signals=False,
        )
        await runner.setup()
        site = web.TCPSite(
            runner,
            self._url.host,
            self._url.port,
        )

        await site.start()

        bus(ServerStatusChanged(status=f"started on {self._url} - press CTRL+C to quit"))

        try:
            while True:
                await asyncio.sleep(3600)
        except asyncio.CancelledError:
            await runner.cleanup()
            bus(ServerStatusChanged(status="shutdown completed"))

    def _prepare_app(self) -> web.Application:
        api = web.Application()
        portfolio.Views(api, self._requester)

        app = web.Application(middlewares=[middleware.error])
        app.add_subapp("/api/", api)

        return app
