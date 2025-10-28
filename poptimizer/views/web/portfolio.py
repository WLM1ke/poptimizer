from pathlib import Path

from aiohttp import web
from jinja2 import Environment, FileSystemLoader, select_autoescape


class Handlers:
    def __init__(self, app: web.Application) -> None:
        self._page = Environment(
            loader=FileSystemLoader(Path(__file__).parent / "templates"),
            autoescape=select_autoescape(["html"]),
        ).get_template("index.html")

        app.add_routes([web.get("/", self.portfolio)])
        app.add_routes([web.get("/accounts/{account}", self.account)])
        app.add_routes([web.get("/forecast", self.forecast)])
        app.add_routes([web.get("/optimization", self.optimization)])
        app.add_routes([web.get("/dividends/{ticker}", self.dividends)])
        app.add_routes([web.get("/settings", self.settings)])

        app.add_routes([web.get("/static/{file_name}", self.static_file)])

    async def portfolio(self, request: web.Request) -> web.StreamResponse:  # noqa: ARG002
        html_content = self._page.render(
            main_template="main_portfolio.html",
            title="Portfolio",
        )

        return web.Response(text=html_content, content_type="text/html")

    async def account(self, request: web.Request) -> web.StreamResponse:
        html_content = self._page.render(
            main_template="main_account.html",
            title=request.match_info["account"],
        )

        return web.Response(text=html_content, content_type="text/html")

    async def forecast(self, request: web.Request) -> web.StreamResponse:  # noqa: ARG002
        html_content = self._page.render(
            main_template="main_forecast.html",
            title="Forecast",
        )

        return web.Response(text=html_content, content_type="text/html")

    async def optimization(self, request: web.Request) -> web.StreamResponse:  # noqa: ARG002
        html_content = self._page.render(
            main_template="main_optimization.html",
            title="Optimization",
        )

        return web.Response(text=html_content, content_type="text/html")

    async def dividends(self, request: web.Request) -> web.StreamResponse:
        html_content = self._page.render(
            main_template="main_dividends.html",
            title=request.match_info["ticker"],
        )

        return web.Response(text=html_content, content_type="text/html")

    async def settings(self, request: web.Request) -> web.StreamResponse:  # noqa: ARG002
        html_content = self._page.render(
            main_template="main_settings.html",
            title="Settings",
        )

        return web.Response(text=html_content, content_type="text/html")

    async def static_file(self, request: web.Request) -> web.StreamResponse:
        return web.FileResponse(Path(__file__).parent / "static" / request.match_info["file_name"])
