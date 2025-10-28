from typing import TYPE_CHECKING

from aiohttp import web

from poptimizer.controllers.bus import msg
from poptimizer.controllers.server import api, http_server, middleware
from poptimizer.views.web import portfolio

if TYPE_CHECKING:
    from pydantic import HttpUrl


def build(
    bus: msg.Bus,
    url: HttpUrl,
) -> http_server.Server:
    sub_app = web.Application()
    api.Handlers(sub_app, bus)

    app = web.Application(middlewares=[middleware.RequestErrorMiddleware()])
    portfolio.Handlers(app)
    app.add_subapp("/api/", sub_app)

    return http_server.Server(
        app,
        url,
    )
