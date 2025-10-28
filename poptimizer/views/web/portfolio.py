from enum import StrEnum, auto
from pathlib import Path

from aiohttp import web
from jinja2 import Environment, FileSystemLoader, select_autoescape
from pydantic import BaseModel

from poptimizer.domain.domain import AccName, Ticker


class Theme(StrEnum):
    SYSTEM = auto()
    LIGHT = auto()
    DARK = auto()


class LayoutModel(BaseModel):
    main_template: str
    title: str
    theme: Theme
    accounts: list[AccName]
    dividends: list[Ticker] = []


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

        app.add_routes([web.get("/static/{path:.*}", self.static_file)])

    async def portfolio(self, request: web.Request) -> web.StreamResponse:  # noqa: ARG002
        layout = LayoutModel(
            main_template="main_portfolio.html",
            title="Portfolio",
            theme=Theme.SYSTEM,
            accounts=[AccName("Account1"), AccName("Account2")],
            dividends=[Ticker("AKMB"), Ticker("GAZP")],
        )

        return await self._render_template(layout)

    async def account(self, request: web.Request) -> web.StreamResponse:
        layout = LayoutModel(
            main_template="main_account.html",
            title=request.match_info["account"],
            theme=Theme.SYSTEM,
            accounts=[AccName("Account1"), AccName("Account2")],
            dividends=[Ticker("AKMB"), Ticker("GAZP")],
        )

        return await self._render_template(layout)

    async def forecast(self, request: web.Request) -> web.StreamResponse:  # noqa: ARG002
        layout = LayoutModel(
            main_template="main_forecast.html",
            title="Forecast",
            theme=Theme.SYSTEM,
            accounts=[AccName("Account1"), AccName("Account2")],
            dividends=[Ticker("AKMB"), Ticker("GAZP")],
        )

        return await self._render_template(layout)

    async def optimization(self, request: web.Request) -> web.StreamResponse:  # noqa: ARG002
        layout = LayoutModel(
            main_template="main_optimization.html",
            title="Optimization",
            theme=Theme.SYSTEM,
            accounts=[AccName("Account1"), AccName("Account2")],
            dividends=[Ticker("AKMB"), Ticker("GAZP")],
        )

        return await self._render_template(layout)

    async def dividends(self, request: web.Request) -> web.StreamResponse:
        layout = LayoutModel(
            main_template="main_dividends.html",
            title=request.match_info["ticker"],
            theme=Theme.SYSTEM,
            accounts=[AccName("Account1"), AccName("Account2")],
            dividends=[Ticker("AKMB"), Ticker("GAZP")],
        )

        return await self._render_template(layout)

    async def settings(self, request: web.Request) -> web.StreamResponse:  # noqa: ARG002
        layout = LayoutModel(
            main_template="main_settings.html",
            title="Settings",
            theme=Theme.SYSTEM,
            accounts=[AccName("Account1"), AccName("Account2")],
            dividends=[Ticker("AKMB"), Ticker("GAZP")],
        )

        return await self._render_template(layout)

    async def _render_template(self, layout: LayoutModel) -> web.StreamResponse:
        html_content = self._page.render(layout=layout)

        return web.Response(text=html_content, content_type="text/html")

    async def static_file(self, request: web.Request) -> web.StreamResponse:
        return web.FileResponse(Path(__file__).parent / "static" / request.match_info["path"])
