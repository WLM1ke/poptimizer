import asyncio

from aiohttp import web
from pydantic import HttpUrl

from poptimizer.app import uow
from poptimizer.core import domain
from poptimizer.ui import api, frontend, middleware


async def run(
    ctx_factory: uow.CtxFactory,
    url: HttpUrl,
) -> None:
    ctx = ctx_factory()
    aiohttp_app = _prepare_app(ctx)

    runner = web.AppRunner(
        aiohttp_app,
        handle_signals=False,
        access_log_class=middleware.AccessLogger,
    )
    await runner.setup()
    site = web.TCPSite(
        runner,
        url.host,
        url.port,
    )

    await site.start()

    ctx.info(f"Server started on {url} - press CTRL+C to quit")

    try:
        while True:
            await asyncio.sleep(3600)
    except asyncio.CancelledError:
        await runner.cleanup()
        ctx.info("Server shutdown completed")


def _prepare_app(ctx: domain.Ctx) -> web.Application:
    sub_app = web.Application()
    api.Handlers(sub_app)

    app = web.Application(middlewares=[middleware.RequestErrorMiddleware(ctx)])
    app.add_subapp("/api/", sub_app)
    frontend.Handlers(app)

    return app
