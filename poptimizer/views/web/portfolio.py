import json
from pathlib import Path
from typing import Any

from aiohttp import web
from jinja2 import Environment, FileSystemLoader, select_autoescape
from pydantic import BaseModel

from poptimizer.controllers.bus import msg
from poptimizer.domain.domain import AccName, Ticker
from poptimizer.domain.settings import Theme
from poptimizer.use_cases.requests import settings as settings_requests


class LayoutModel(BaseModel):
    main_template: str
    title: str
    path: str
    theme: Theme
    accounts: list[AccName]
    dividends: list[Ticker]


class Handlers:
    def __init__(self, app: web.Application, bus: msg.Bus) -> None:
        self._bus = bus
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

    async def portfolio(self, request: web.Request) -> web.StreamResponse:
        theme_dto = await self._bus.request(settings_requests.GetTheme())

        layout = LayoutModel(
            main_template="portfolio.html",
            title="Portfolio",
            path=request.path,
            theme=theme_dto.theme,
            accounts=[AccName("Account1"), AccName("Account2")],
            dividends=[Ticker("AKMB"), Ticker("GAZP")],
        )

        return await self._render_page(layout, request)

    async def account(self, request: web.Request) -> web.StreamResponse:
        theme_dto = await self._bus.request(settings_requests.GetTheme())  # type: ignore[assignment]
        layout = LayoutModel(
            main_template="account.html",
            title=request.match_info["account"],
            path=request.path,
            theme=theme_dto.theme,  # type: ignore[attr-defined]
            accounts=[AccName("Account1"), AccName("Account2")],
            dividends=[Ticker("AKMB"), Ticker("GAZP")],
        )

        return await self._render_page(layout, request)

    async def forecast(self, request: web.Request) -> web.StreamResponse:
        theme_dto = await self._bus.request(settings_requests.GetTheme())
        layout = LayoutModel(
            main_template="forecast.html",
            title="Forecast",
            path=request.path,
            theme=theme_dto.theme,
            accounts=[AccName("Account1"), AccName("Account2")],
            dividends=[Ticker("AKMB"), Ticker("GAZP")],
        )

        return await self._render_page(layout, request)

    async def optimization(self, request: web.Request) -> web.StreamResponse:
        theme_dto = await self._bus.request(settings_requests.GetTheme())
        layout = LayoutModel(
            main_template="optimization.html",
            title="Optimization",
            path=request.path,
            theme=theme_dto.theme,
            accounts=[AccName("Account1"), AccName("Account2")],
            dividends=[Ticker("AKMB"), Ticker("GAZP")],
        )

        return await self._render_page(layout, request)

    async def dividends(self, request: web.Request) -> web.StreamResponse:
        theme_dto = await self._bus.request(settings_requests.GetTheme())
        layout = LayoutModel(
            main_template="dividends.html",
            title=request.match_info["ticker"],
            path=request.path,
            theme=theme_dto.theme,
            accounts=[AccName("Account1"), AccName("Account2")],
            dividends=[Ticker("AKMB"), Ticker("GAZP")],
        )

        return await self._render_page(layout, request)

    async def settings(self, request: web.Request) -> web.StreamResponse:
        theme_dto = await self._bus.request(settings_requests.GetTheme())
        layout = LayoutModel(
            main_template="settings.html",
            title="Settings",
            path=request.path,
            theme=theme_dto.theme,
            accounts=[AccName("Account1"), AccName("Account2")],
            dividends=[Ticker("AKMB"), Ticker("GAZP")],
        )

        return await self._render_page(layout, request)

    async def _render_page(self, layout: LayoutModel, request: web.Request) -> web.StreamResponse:
        template = "index.html"
        headers = {}

        if request.headers.get("HX-Boosted") == "true":
            template = "body.html"
            headers = prepare_event_header("set_title")

        return web.Response(
            text=self._env.get_template(template).render(layout=layout),
            content_type="text/html",
            headers=headers,
        )

    async def theme_handler(self, request: web.Request) -> web.StreamResponse:
        theme = request.match_info["theme"]

        if theme not in Theme:
            return web.HTTPNotFound(text=f"Invalid theme - {theme}")

        await self._bus.request(settings_requests.UpdateTheme(theme=Theme(theme)))

        html = self._env.get_template(f"theme/{theme}.html").render()

        return web.Response(
            text=html,
            content_type="text/html",
            headers=prepare_event_header("set_theme", theme=theme),
        )

    async def static_file(self, request: web.Request) -> web.StreamResponse:
        file_path = Path(__file__).parent / "static" / request.match_info["path"]

        return web.FileResponse(file_path)


def prepare_event_header(cmd: str, **kwargs: Any) -> dict[str, str]:
    payload = {"po:cmd": {"target": "body", "cmd": cmd, "args": kwargs}}

    return {"HX-Trigger-After-Settle": json.dumps(payload)}
