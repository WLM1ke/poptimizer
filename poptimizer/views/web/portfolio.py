from enum import StrEnum, auto
from pathlib import Path

from aiohttp import web
from jinja2 import Environment, FileSystemLoader, select_autoescape
from pydantic import BaseModel, Field

from poptimizer.domain.domain import AccName, Ticker


class Theme(StrEnum):
    SYSTEM = auto()
    LIGHT = auto()
    DARK = auto()


class LayoutModel(BaseModel):
    main_template: str = ""
    title: str = ""
    theme: Theme = Theme.SYSTEM
    accounts: list[AccName] = Field(default_factory=list[AccName])
    dividends: list[Ticker] = Field(default_factory=list[Ticker])


class Handlers:
    def __init__(self, app: web.Application) -> None:
        self._env = Environment(
            loader=FileSystemLoader(Path(__file__).parent / "templates"),
            autoescape=select_autoescape(["html"]),
        )

        app.add_routes([web.get("/", self.portfolio)])
        app.add_routes([web.get("/accounts/{account}", self.account)])
        app.add_routes([web.get("/forecast", self.forecast)])
        app.add_routes([web.get("/optimization", self.optimization)])
        app.add_routes([web.get("/dividends/{ticker}", self.dividends)])
        app.add_routes([web.get("/settings", self.settings)])
        app.add_routes([web.put("/theme/{theme}", self.theme_handler)])

        app.add_routes([web.get("/static/{path:.*}", self.static_file)])

    async def portfolio(self, request: web.Request) -> web.StreamResponse:  # noqa: ARG002
        layout = LayoutModel(
            main_template="main_portfolio.html",
            title="Portfolio",
            theme=Theme.SYSTEM,
            accounts=[AccName("Account1"), AccName("Account2")],
            dividends=[Ticker("AKMB"), Ticker("GAZP")],
        )

        return await self._render_page(layout)

    async def account(self, request: web.Request) -> web.StreamResponse:
        layout = LayoutModel(
            main_template="main_account.html",
            title=request.match_info["account"],
            theme=Theme.SYSTEM,
            accounts=[AccName("Account1"), AccName("Account2")],
            dividends=[Ticker("AKMB"), Ticker("GAZP")],
        )

        return await self._render_page(layout)

    async def forecast(self, request: web.Request) -> web.StreamResponse:  # noqa: ARG002
        layout = LayoutModel(
            main_template="main_forecast.html",
            title="Forecast",
            theme=Theme.SYSTEM,
            accounts=[AccName("Account1"), AccName("Account2")],
            dividends=[Ticker("AKMB"), Ticker("GAZP")],
        )

        return await self._render_page(layout)

    async def optimization(self, request: web.Request) -> web.StreamResponse:  # noqa: ARG002
        layout = LayoutModel(
            main_template="main_optimization.html",
            title="Optimization",
            theme=Theme.SYSTEM,
            accounts=[AccName("Account1"), AccName("Account2")],
            dividends=[Ticker("AKMB"), Ticker("GAZP")],
        )

        return await self._render_page(layout)

    async def dividends(self, request: web.Request) -> web.StreamResponse:
        layout = LayoutModel(
            main_template="main_dividends.html",
            title=request.match_info["ticker"],
            theme=Theme.SYSTEM,
            accounts=[AccName("Account1"), AccName("Account2")],
            dividends=[Ticker("AKMB"), Ticker("GAZP")],
        )

        return await self._render_page(layout)

    async def settings(self, request: web.Request) -> web.StreamResponse:  # noqa: ARG002
        layout = LayoutModel(
            main_template="main_settings.html",
            title="Settings",
            theme=Theme.SYSTEM,
            accounts=[AccName("Account1"), AccName("Account2")],
            dividends=[Ticker("AKMB"), Ticker("GAZP")],
        )

        return await self._render_page(layout)

    async def _render_page(self, layout: LayoutModel) -> web.StreamResponse:
        html = self._env.get_template("index.html").render(layout=layout)

        return web.Response(text=html, content_type="text/html")

    async def theme_handler(self, request: web.Request) -> web.StreamResponse:
        theme = request.match_info["theme"]

        if theme not in Theme:
            return web.HTTPNotFound(text=f"Invalid theme - {theme}")

        html = self._env.get_template(f"theme_{theme}.html").render()

        return web.Response(text=html, content_type="text/html")

    async def static_file(self, request: web.Request) -> web.StreamResponse:
        file_path = Path(__file__).parent / "static" / request.match_info["path"]

        return web.FileResponse(file_path)
