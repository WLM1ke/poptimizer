import asyncio
import http
import json
import logging
from pathlib import Path
from typing import Any

from aiohttp import typedefs, web
from jinja2 import Environment, FileSystemLoader, select_autoescape
from pydantic import BaseModel, TypeAdapter, ValidationError

from poptimizer import errors
from poptimizer.controllers.bus import msg
from poptimizer.domain import domain
from poptimizer.domain.div import status
from poptimizer.domain.domain import AccName, Ticker
from poptimizer.domain.portfolio import forecasts, portfolio
from poptimizer.domain.settings import Settings, Theme
from poptimizer.use_cases import handler


class Layout(BaseModel):
    title: str
    path: str
    poll: bool
    theme: Theme
    accounts: list[AccName]
    dividends: list[Ticker]


class Main(BaseModel):
    template: str


class Card(BaseModel):
    upper: str
    main: str
    lower: str


class Position(BaseModel):
    ticker: domain.Ticker
    quantity: int
    lot: int
    price: float
    value: float


class Portfolio(BaseModel):
    template: str
    account: AccName | None = None
    card: Card
    value: float
    cash: int
    positions: list[Position]


class Forecasts(BaseModel):
    template: str
    card: Card
    positions: list[forecasts.Position]


class Handlers:
    def __init__(self, app: web.Application, bus: msg.Bus) -> None:
        self._lgr = logging.getLogger()
        self._bus = bus
        self._env = Environment(
            loader=FileSystemLoader(Path(__file__).parent / "templates"),
            autoescape=select_autoescape(["html"]),
        )

        app.middlewares.append(self._alerts_middleware)

        app.add_routes([web.get("/", bus.wrap(self.portfolio))])
        app.add_routes([web.get("/accounts/{account}", bus.wrap(self.account))])
        app.add_routes([web.patch("/accounts/{account}/{ticker}", bus.wrap(self.update_position))])
        app.add_routes([web.get("/forecast", bus.wrap(self.forecast))])
        app.add_routes([web.get("/optimization", bus.wrap(self.optimization))])
        app.add_routes([web.get("/dividends/{ticker}", bus.wrap(self.dividends))])
        app.add_routes([web.get("/settings", bus.wrap(self.settings))])
        app.add_routes([web.put("/theme/{theme}", bus.wrap(self.theme_handler))])

        app.add_routes([web.get("/static/{path:.*}", self.static_file)])

    async def portfolio(self, ctx: handler.Ctx, req: web.Request) -> web.StreamResponse:
        port = await ctx.get(portfolio.Portfolio)

        value = port.value()
        positions = [
            Position(
                ticker=position.ticker,
                quantity=position.quantity(),
                lot=position.lot,
                price=position.price,
                value=position.value(),
            )
            for position in port.positions
            if position.quantity() > 0
        ]

        main = Portfolio(
            template="portfolio.html",
            card=Card(
                upper=f"Date: {port.day}",
                main=f"Value: {_format_float(value, 0)} ₽",
                lower=f"Positions: {port.open_positions()} / Effective: {_format_float(port.effective_positions, 0)}",
            ),
            value=value,
            cash=port.cash_value(),
            positions=sorted(positions, key=lambda x: x.value, reverse=True),
        )

        return await self._render_page(
            ctx,
            "Portfolio",
            req,
            main,
        )

    async def account(self, ctx: handler.Ctx, req: web.Request) -> web.StreamResponse:
        account = domain.AccName(req.match_info["account"])

        async with asyncio.TaskGroup() as tg:
            port_task = tg.create_task(ctx.get(portfolio.Portfolio))
            settings_task = tg.create_task(ctx.get(Settings))

        main = _prepare_account(
            port_task.result(),
            account,
            hide_zero_positions=settings_task.result().hide_zero_positions,
        )

        return await self._render_page(
            ctx,
            account,
            req,
            main,
        )

    async def update_position(self, ctx: handler.Ctx, req: web.Request) -> web.StreamResponse:
        account = domain.AccName(req.match_info["account"])
        ticker = domain.Ticker(req.match_info["ticker"])
        quantity = TypeAdapter(int).validate_python((await req.post()).get("quantity"))

        async with asyncio.TaskGroup() as tg:
            port_task = tg.create_task(ctx.get_for_update(portfolio.Portfolio))
            settings_task = tg.create_task(ctx.get(Settings))

        port = port_task.result()
        port.update_position(account, ticker, quantity)

        main = _prepare_account(
            port,
            account,
            hide_zero_positions=settings_task.result().hide_zero_positions,
        )

        return web.Response(
            text=self._env.get_template("main/account.html").render(
                main=main,
                format_float=_format_float,
                format_percent=_format_percent,
            ),
            content_type="text/html",
        )

    async def forecast(self, ctx: handler.Ctx, req: web.Request) -> web.StreamResponse:
        async with asyncio.TaskGroup() as tg:
            port_task = tg.create_task(ctx.get(portfolio.Portfolio))
            forecasts_task = tg.create_task(ctx.get(forecasts.Forecast))

        forecast = forecasts_task.result()

        outdated = ""
        poll = False

        if port_task.result().ver != forecast.portfolio_ver:
            outdated = "outdated"
            poll = True

        main = Forecasts(
            template="forecast.html",
            card=Card(
                upper=f"Date: {forecast.day} {outdated}",
                main=(f"Mean: {_format_percent(forecast.mean)} / Std: {_format_percent(forecast.std)}"),
                lower=(
                    f"Interval: {forecast.forecast_days} days / "
                    f"Risk aversion: {_format_percent(1 - forecast.risk_tolerance)} %"
                ),
            ),
            positions=forecast.positions,
        )

        return await self._render_page(
            ctx,
            "Forecast",
            req,
            main,
            poll=poll,
        )

    async def optimization(self, ctx: handler.Ctx, req: web.Request) -> web.StreamResponse:
        main = Main(template="optimization.html")

        return await self._render_page(
            ctx,
            "Optimization",
            req,
            main,
        )

    async def dividends(self, ctx: handler.Ctx, req: web.Request) -> web.StreamResponse:
        main = Main(template="dividends.html")

        return await self._render_page(
            ctx,
            req.match_info["ticker"],
            req,
            main,
        )

    async def settings(self, ctx: handler.Ctx, req: web.Request) -> web.StreamResponse:
        main = Main(template="settings.html")

        return await self._render_page(
            ctx,
            "Settings",
            req,
            main,
        )

    async def _render_page(
        self,
        ctx: handler.Ctx,
        title: str,
        req: web.Request,
        main: Any,
        *,
        poll: bool = False,
    ) -> web.StreamResponse:
        async with asyncio.TaskGroup() as tg:
            settings_task = tg.create_task(ctx.get(Settings))
            port_task = tg.create_task(ctx.get(portfolio.Portfolio))
            div_task = tg.create_task(ctx.get(status.DivStatus))

        layout = Layout(
            title=title,
            path=req.path,
            poll=poll,
            theme=settings_task.result().theme,
            accounts=sorted(port_task.result().account_names),
            dividends=sorted({row.ticker for row in div_task.result().df}),
        )

        match req.headers.get("HX-Request") == "true":
            case True:
                template = "body.html"
                headers = _prepare_event_header("set_title")
            case False:
                template = "index.html"
                headers = {}

        return web.Response(
            text=self._env.get_template(template).render(
                layout=layout,
                main=main,
                format_float=_format_float,
                format_percent=_format_percent,
            ),
            content_type="text/html",
            headers=headers,
        )

    async def theme_handler(self, ctx: handler.Ctx, req: web.Request) -> web.StreamResponse:
        theme = req.match_info["theme"]

        if theme not in Theme:
            return web.HTTPNotFound(text=f"Invalid theme - {theme}")

        settings = await ctx.get_for_update(Settings)
        settings.update_theme(Theme(theme))

        return web.Response(
            text=self._env.get_template(f"theme/{theme}.html").render(),
            content_type="text/html",
            headers=_prepare_event_header("set_theme", theme=theme),
        )

    @web.middleware
    async def _alerts_middleware(
        self,
        request: web.Request,
        handler: typedefs.Handler,
    ) -> web.StreamResponse:
        try:
            return await handler(request)
        except (errors.AdapterError, errors.ControllersError) as err:
            self._lgr.warning("Can't handle request - %s", err)

            return self._alert(http.HTTPStatus.INTERNAL_SERVER_ERROR, f"{err.__class__.__name__}: {','.join(err.args)}")
        except (errors.DomainError, errors.UseCasesError) as err:
            self._lgr.warning("Can't handle request - %s", err)

            return self._alert(http.HTTPStatus.BAD_REQUEST, f"{err.__class__.__name__}: {','.join(err.args)}")
        except ValidationError as err:
            self._lgr.warning("Can't handle request - %s", err)
            msg = ",".join(desc["msg"] for desc in err.errors())

            return self._alert(http.HTTPStatus.BAD_REQUEST, f"{err.__class__.__name__}: {msg}")

    def _alert(self, code: int, alert: str) -> web.Response:
        return web.Response(
            status=code,
            text=self._env.get_template("components/alert.html").render(alert=alert),
            content_type="text/html",
        )

    async def static_file(self, req: web.Request) -> web.StreamResponse:
        file_path = Path(__file__).parent / "static" / req.match_info["path"]

        return web.FileResponse(file_path)


def _prepare_account(
    portfolio: portfolio.Portfolio,
    account: domain.AccName,
    *,
    hide_zero_positions: bool,
) -> Portfolio:
    value = portfolio.value(account)

    positions = [
        Position(
            ticker=position.ticker,
            quantity=position.quantity(account),
            lot=position.lot,
            price=position.price,
            value=position.value(account),
        )
        for position in portfolio.positions
        if position.quantity(account) > 0 or not hide_zero_positions
    ]

    return Portfolio(
        template="account.html",
        account=account,
        card=Card(
            upper=f"Date: {portfolio.day}",
            main=f"Value: {_format_float(value, 0)} ₽",
            lower=f"Positions: {portfolio.open_positions(account)} / {len(portfolio.positions)}",
        ),
        value=value,
        cash=portfolio.cash_value(),
        positions=positions,
    )


def _prepare_event_header(cmd: str, **kwargs: Any) -> dict[str, str]:
    payload = {"po:cmd": {"target": "body", "cmd": cmd, "args": kwargs}}

    return {"HX-Trigger-After-Settle": json.dumps(payload)}


def _format_float(number: float, decimals: int | None = None) -> str:
    match decimals:
        case None:
            rez = f"{number:_}"
        case _:
            rez = f"{number:_.{decimals}f}"

    return rez.replace("_", " ").replace(".", ",")


def _format_percent(number: float) -> str:
    return f"{_format_float(number * 100, 1)} %"
