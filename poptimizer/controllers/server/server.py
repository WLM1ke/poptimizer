from typing import TYPE_CHECKING

from aiohttp import web

from poptimizer.controllers.bus import msg
from poptimizer.controllers.server import api, frontend, http_server, middleware

if TYPE_CHECKING:
    from pydantic import HttpUrl


def build(
    bus: msg.Bus,
    url: HttpUrl,
) -> http_server.Server:
    sub_app = web.Application()
    api.Handlers(sub_app, bus)

    app = web.Application(middlewares=[middleware.RequestErrorMiddleware()])
    app.add_subapp("/api/", sub_app)
    frontend.Handlers(app)

    return http_server.Server(
        app,
        url,
    )
