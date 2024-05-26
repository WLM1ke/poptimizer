from collections.abc import Callable

from aiohttp import web
from pydantic import HttpUrl

from poptimizer.domain.service import portfolio
from poptimizer.domain.service.data.div import raw
from poptimizer.service.common import logging, uow
from poptimizer.ui import api, frontend, http, middleware


async def run(
    logging_service: logging.Service,
    ctx_factory: uow.CtxFactory,
    url: HttpUrl,
    backup_action: Callable[[], None],
) -> None:
    handlers = _prepare_handlers(
        logging_service,
        ctx_factory,
        lambda: None,
        backup_action,
    )
    server = http.Server(
        logging_service,
        handlers,
        url,
    )

    await server()


def _prepare_handlers(
    logging_service: logging.Service,
    ctx_factory: uow.CtxFactory,
    optimization_action: Callable[[], None],
    backup_action: Callable[[], None],
) -> web.Application:
    sub_app = web.Application()
    api.Handlers(
        sub_app,
        ctx_factory,
        portfolio.PortfolioEditService(optimization_action),
        raw.DividendsEditService(backup_action),
    )

    app = web.Application(middlewares=[middleware.RequestErrorMiddleware(logging_service)])
    app.add_subapp("/api/", sub_app)
    frontend.Handlers(app)

    return app
