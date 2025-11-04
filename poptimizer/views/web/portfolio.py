import json
from pathlib import Path
from typing import Any

from aiohttp import web
from jinja2 import Environment, FileSystemLoader, select_autoescape
from pydantic import BaseModel

from poptimizer.controllers.bus import msg
from poptimizer.domain.domain import AccName, Ticker
from poptimizer.domain.settings import Settings, Theme
from poptimizer.use_cases import handler


class LayoutModel(BaseModel):
    main_template: str
    title: str
    path: str
    theme: Theme
    accounts: list[AccName]
    dividends: list[Ticker]


class Handlers:
    def __init__(self, app: web.Application, bus: msg.Bus) -> None:
        self._env = Environment(
            loader=FileSystemLoader(Path(__file__).parent / "templates"),
            autoescape=select_autoescape(["html"]),
        )

        app.add_routes([web.get("/", bus.wrap(self.portfolio))])
        app.add_routes([web.get("/accounts/{account}", bus.wrap(self.account))])
        app.add_routes([web.get("/forecast", bus.wrap(self.forecast))])
        app.add_routes([web.get("/optimization", bus.wrap(self.optimization))])
        app.add_routes([web.get("/dividends/{ticker}", bus.wrap(self.dividends))])
        app.add_routes([web.get("/settings", bus.wrap(self.settings))])
        app.add_routes([web.put("/theme/{theme}", bus.wrap(self.theme_handler))])

        app.add_routes([web.get("/static/{path:.*}", self.static_file)])

    async def portfolio(self, ctx: handler.Ctx, req: web.Request) -> web.StreamResponse:
        settings = await ctx.get(Settings)

        layout = LayoutModel(
            main_template="portfolio.html",
            title="Portfolio",
            path=req.path,
            theme=settings.theme,
            accounts=[AccName("Account1"), AccName("Account2")],
            dividends=[Ticker("AKMB"), Ticker("GAZP")],
        )

        return await self._render_page(layout, req)

    async def account(self, ctx: handler.Ctx, req: web.Request) -> web.StreamResponse:
        settings = await ctx.get(Settings)

        layout = LayoutModel(
            main_template="account.html",
            title=req.match_info["account"],
            path=req.path,
            theme=settings.theme,
            accounts=[AccName("Account1"), AccName("Account2")],
            dividends=[Ticker("AKMB"), Ticker("GAZP")],
        )

        return await self._render_page(layout, req)

    async def forecast(self, ctx: handler.Ctx, req: web.Request) -> web.StreamResponse:
        settings = await ctx.get(Settings)

        layout = LayoutModel(
            main_template="forecast.html",
            title="Forecast",
            path=req.path,
            theme=settings.theme,
            accounts=[AccName("Account1"), AccName("Account2")],
            dividends=[Ticker("AKMB"), Ticker("GAZP")],
        )

        return await self._render_page(layout, req)

    async def optimization(self, ctx: handler.Ctx, req: web.Request) -> web.StreamResponse:
        settings = await ctx.get(Settings)

        layout = LayoutModel(
            main_template="optimization.html",
            title="Optimization",
            path=req.path,
            theme=settings.theme,
            accounts=[AccName("Account1"), AccName("Account2")],
            dividends=[Ticker("AKMB"), Ticker("GAZP")],
        )

        return await self._render_page(layout, req)

    async def dividends(self, ctx: handler.Ctx, req: web.Request) -> web.StreamResponse:
        settings = await ctx.get(Settings)

        layout = LayoutModel(
            main_template="dividends.html",
            title=req.match_info["ticker"],
            path=req.path,
            theme=settings.theme,
            accounts=[AccName("Account1"), AccName("Account2")],
            dividends=[Ticker("AKMB"), Ticker("GAZP")],
        )

        return await self._render_page(layout, req)

    async def settings(self, ctx: handler.Ctx, req: web.Request) -> web.StreamResponse:
        settings = await ctx.get(Settings)

        layout = LayoutModel(
            main_template="settings.html",
            title="Settings",
            path=req.path,
            theme=settings.theme,
            accounts=[AccName("Account1"), AccName("Account2")],
            dividends=[Ticker("AKMB"), Ticker("GAZP")],
        )

        return await self._render_page(layout, req)

    async def _render_page(self, layout: LayoutModel, req: web.Request) -> web.StreamResponse:
        template = "index.html"
        headers = {}

        if req.headers.get("HX-Boosted") == "true":
            template = "body.html"
            headers = prepare_event_header("set_title")

        return web.Response(
            text=self._env.get_template(template).render(layout=layout),
            content_type="text/html",
            headers=headers,
        )

    async def theme_handler(self, ctx: handler.Ctx, req: web.Request) -> web.StreamResponse:
        theme = req.match_info["theme"]

        if theme not in Theme:
            return web.HTTPNotFound(text=f"Invalid theme - {theme}")

        settings = await ctx.get_for_update(Settings)
        settings.update_theme(Theme(theme))

        html = self._env.get_template(f"theme/{theme}.html").render()

        return web.Response(
            text=html,
            content_type="text/html",
            headers=prepare_event_header("set_theme", theme=theme),
        )

    async def static_file(self, req: web.Request) -> web.StreamResponse:
        file_path = Path(__file__).parent / "static" / req.match_info["path"]

        return web.FileResponse(file_path)


def prepare_event_header(cmd: str, **kwargs: Any) -> dict[str, str]:
    payload = {"po:cmd": {"target": "body", "cmd": cmd, "args": kwargs}}

    return {"HX-Trigger-After-Settle": json.dumps(payload)}
