from collections.abc import Callable

from aiohttp import web
from pydantic import HttpUrl

from poptimizer.adapter import telegram
from poptimizer.adapters import backup
from poptimizer.adapters.server import Server
from poptimizer.data import services
from poptimizer.service import uow
from poptimizer.ui import api, frontend, middleware


async def run(
    telegram_lgr: telegram.Logger,
    ctx_factory: uow.CtxFactory,
    url: HttpUrl,
    backup_srv: backup.Service,
) -> None:
    handlers = _prepare_handlers(telegram_lgr, ctx_factory, lambda: None, backup_srv.backup)
    server = Server(
        telegram_lgr,
        handlers,
        url,
    )

    await server()


def _prepare_handlers(
    telegram_lgr: telegram.Logger,
    ctx_factory: uow.CtxFactory,
    optimization_action: Callable[[], None],
    backup_action: Callable[[], None],
) -> web.Application:
    sub_app = web.Application()
    api.Handlers(sub_app, ctx_factory, services.Portfolio(optimization_action), services.Dividends(backup_action))

    app = web.Application(middlewares=[middleware.RequestErrorMiddleware(telegram_lgr)])
    app.add_subapp("/api/", sub_app)
    frontend.Handlers(app)

    return app
