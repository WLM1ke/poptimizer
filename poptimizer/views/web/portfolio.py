from pathlib import Path

from aiohttp import web
from jinja2 import Environment, FileSystemLoader, select_autoescape


class Handlers:
    def __init__(self, app: web.Application) -> None:
        self._env = Environment(
            loader=FileSystemLoader(Path(__file__).parent / "templates"),
            autoescape=select_autoescape(["html"]),
        )

        app.add_routes([web.get("/new", self.portfolio)])
        app.add_routes([web.get("/static/{file_name}", self.static_file)])

    async def portfolio(self, request: web.Request) -> web.StreamResponse:  # noqa: ARG002
        html_content = self._env.get_template("index.html").render()

        return web.Response(text=html_content, content_type="text/html")

    async def static_file(self, request: web.Request) -> web.StreamResponse:
        return web.FileResponse(Path(__file__).parent / "static" / request.match_info["file_name"])
