from pathlib import Path
from typing import Final

from aiohttp import web

_STATIC_PATH: Final = Path(__file__).parents[2] / "static"


class Views:
    def __init__(self, app: web.Application) -> None:
        app.add_routes([web.get("/favicon.ico", self.favicon)])
        app.add_routes([web.static("/_app/", _STATIC_PATH / "_app/")])
        app.add_routes([web.get(r"/{rest:.*}", self.index)])

    async def index(self, request: web.Request) -> web.StreamResponse:  # noqa: ARG002
        return web.FileResponse(_STATIC_PATH / "index.html")

    async def favicon(self, request: web.Request) -> web.StreamResponse:  # noqa: ARG002
        return web.FileResponse(_STATIC_PATH / "favicon.ico")
