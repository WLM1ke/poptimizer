import asyncio

from aiohttp import web
from pydantic import HttpUrl

from poptimizer.adapters import backup, telegram, uow
from poptimizer.data import services
from poptimizer.ui import api, frontend, middleware


async def run(
    telegram_lgr: telegram.Logger,
    ctx_factory: uow.CtxFactory,
    url: HttpUrl,
    backup_srv: backup.Service,
) -> None:
    aiohttp_app = _prepare_app(ctx_factory, backup_srv)

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

    telegram_lgr.info(f"Server started on {url} - press CTRL+C to quit")

    try:
        await asyncio.Event().wait()
    except asyncio.CancelledError:
        await runner.cleanup()
        telegram_lgr.info("Server shutdown completed")


def _prepare_app(
    ctx_factory: uow.CtxFactory,
    backup_srv: backup.Service,
) -> web.Application:
    sub_app = web.Application()
    api.Handlers(sub_app, ctx_factory, services.Portfolio(), services.Dividends(backup_srv.backup))

    app = web.Application(middlewares=[middleware.RequestErrorMiddleware(ctx_factory())])
    app.add_subapp("/api/", sub_app)
    frontend.Handlers(app)

    return app
