import asyncio

from aiohttp import web
from pydantic import HttpUrl

from poptimizer.controllers import middleware, portfolio
from poptimizer.core import domain


class ServerStatusChanged(domain.Event):
    status: str


class APIServerService:
    def __init__(
        self,
        url: HttpUrl,
    ) -> None:
        self._url = url

    async def run(self, ctx: domain.SrvCtx) -> None:
        aiohttp_app = self._prepare_app(ctx)

        runner = web.AppRunner(
            aiohttp_app,
            handle_signals=False,
        )
        await runner.setup()
        site = web.TCPSite(
            runner,
            self._url.host,
            self._url.port,
        )

        await site.start()

        ctx.publish(ServerStatusChanged(status=f"started on {self._url} - press CTRL+C to quit"))

        try:
            while True:
                await asyncio.sleep(3600)
        except asyncio.CancelledError:
            await runner.cleanup()
            ctx.publish(ServerStatusChanged(status="shutdown completed"))

    def _prepare_app(self, ctx: domain.SrvCtx) -> web.Application:
        api = web.Application()
        portfolio.Views(api, ctx)

        app = web.Application(middlewares=[middleware.error])
        app.add_subapp("/api/", api)

        return app
