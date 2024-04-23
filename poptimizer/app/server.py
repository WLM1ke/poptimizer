import asyncio

from aiohttp import web
from pydantic import HttpUrl

from poptimizer.adapters import uow
from poptimizer.data import services
from poptimizer.ui import api, frontend, middleware


async def run(
    ctx_factory: uow.CtxFactory,
    url: HttpUrl,
) -> None:
    aiohttp_app = _prepare_app(ctx_factory)

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

    ctx = ctx_factory()
    ctx.info(f"Server started on {url} - press CTRL+C to quit")

    try:
        while True:
            await asyncio.sleep(3600)
    except asyncio.CancelledError:
        await runner.cleanup()
        ctx.info("Server shutdown completed")


def _prepare_app(
    ctx_factory: uow.CtxFactory,
) -> web.Application:
    sub_app = web.Application()
    api.Handlers(sub_app, ctx_factory, services.Portfolio(), services.Dividends())

    app = web.Application(middlewares=[middleware.RequestErrorMiddleware(ctx_factory())])
    app.add_subapp("/api/", sub_app)
    frontend.Handlers(app)

    return app
