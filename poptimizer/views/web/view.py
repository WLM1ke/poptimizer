import asyncio
import http
import logging
from datetime import timedelta
from enum import StrEnum, auto
from pathlib import Path
from typing import Any, Final
from urllib import parse

from aiohttp import typedefs, web
from jinja2 import Environment, FileSystemLoader, select_autoescape
from pydantic import BaseModel, Field, TypeAdapter, ValidationError

from poptimizer import errors
from poptimizer.controllers.bus import msg
from poptimizer.domain import domain
from poptimizer.domain.div import raw, reestry, status
from poptimizer.domain.domain import AccName, Ticker, date
from poptimizer.domain.portfolio import forecasts, portfolio
from poptimizer.use_cases import handler
from poptimizer.views.web import models

_YEAR_IN_SECONDS: Final = int(timedelta(days=365).total_seconds())


class Layout(BaseModel):
    title: str
    selected_path: str
    poll: bool
    theme: models.Theme
    accounts: list[AccName]
    dividends: list[Ticker]


class Row(BaseModel):
    label: str
    value: str


class Card(BaseModel):
    upper: str
    main: str
    row1: Row
    row2: Row
    row3: Row


class Position(BaseModel):
    ticker: domain.Ticker
    quantity: int
    lot: int
    price: float
    value: float


class Portfolio(BaseModel):
    template: str
    card: Card
    value: float
    cash: int
    positions: list[Position]


class Account(BaseModel):
    template: str
    account: AccName
    card: Card
    value: float
    cash: int
    positions: list[Position]


class Forecast(BaseModel):
    template: str
    card: Card
    positions: list[forecasts.Position]


class Optimize(BaseModel):
    template: str
    card: Card
    breakeven: float
    buy: list[forecasts.Position]
    sell: list[forecasts.Position]


class DivStatus(StrEnum):
    EXTRA = auto()
    OK = auto()
    MISSED = auto()


class DivRow(BaseModel):
    day: domain.Day
    dividend: float = Field(gt=0)
    status: DivStatus

    def to_tuple(self) -> tuple[date, float]:
        return self.day, self.dividend


class Dividends(BaseModel):
    template: str
    ticker: domain.UID
    dividends: list[DivRow]

    @property
    def day(self) -> domain.Day:
        if len(self.dividends):
            return self.dividends[-1].day

        return date.today()

    @property
    def dividend(self) -> float:
        if len(self.dividends):
            return self.dividends[-1].dividend

        return 1


class Settings(BaseModel):
    template: str
    hide_accounts_zero_positions: bool = Field(default=False)
    accounts: list[AccName]
    exclude: list[domain.Ticker]


class Provider:
    def __init__(self, bus: msg.Bus) -> None:
        self._lgr = logging.getLogger()
        self._app = web.Application(middlewares=[self._alerts_middleware])
        self._bus = bus
        self._env = Environment(
            loader=FileSystemLoader(Path(__file__).parent / "templates"),
            autoescape=select_autoescape(["html"]),
        )

        routes = (
            (
                web.get,
                "/",
                self._portfolio,
            ),
            (
                web.get,
                "/accounts/{account}",
                self._account,
            ),
            (
                web.patch,
                "/accounts/{account}",
                self._account_toggle_positions,
            ),
            (
                web.patch,
                "/accounts/{account}/{ticker}",
                self._update_position,
            ),
            (
                web.get,
                "/forecast",
                self._forecast,
            ),
            (
                web.get,
                "/optimization",
                self._optimization,
            ),
            (
                web.get,
                "/dividends/{ticker}",
                self._dividends,
            ),
            (
                web.patch,
                "/dividends/{ticker}/add",
                self._dividend_add,
            ),
            (
                web.patch,
                "/dividends/{ticker}/remove",
                self._dividend_remove,
            ),
            (
                web.get,
                "/settings",
                self._settings,
            ),
            (
                web.patch,
                "/settings/hide_zero_positions",
                self._hide_zero_positions,
            ),
            (
                web.post,
                "/accounts",
                self._create_acount,
            ),
            (
                web.delete,
                "/accounts/{account}",
                self._remove_acount,
            ),
            (
                web.post,
                "/exclude",
                self._exclude_ticker,
            ),
            (
                web.delete,
                "/exclude/{ticker}",
                self._not_exclude_ticker,
            ),
            (
                web.patch,
                "/theme/{theme}",
                self._theme,
            ),
        )

        for method, path, unwrapped_handler in routes:
            self._app.add_routes([method(path, bus.wrap(unwrapped_handler))])

        self._app.add_routes([web.get("/{path:.*}", self._static_file)])

    def __call__(self) -> web.Application:
        return self._app

    async def _portfolio(self, ctx: handler.Ctx, req: web.Request) -> web.StreamResponse:
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
                row1=Row(label="Effective positions", value=f"{_format_float(port.effective_positions, 0)}"),
                row2=Row(label="Open positions", value=f"{port.open_positions()}"),
                row3=Row(label="Total positions", value=f"{_format_float(len(port.positions), 0)}"),
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

    async def _account(self, ctx: handler.Ctx, req: web.Request) -> web.StreamResponse:
        account = domain.AccName(req.match_info["account"])
        cookie = models.Cookie.from_request(req)

        main = _prepare_account(
            await ctx.get(portfolio.Portfolio),
            account,
            hide_zero_positions=cookie.hide_zero_positions,
        )

        return await self._render_page(
            ctx,
            account,
            req,
            main,
        )

    async def _account_toggle_positions(self, ctx: handler.Ctx, req: web.Request) -> web.StreamResponse:
        account = domain.AccName(req.match_info["account"])
        cookie = models.Cookie.from_request(req)

        cookie.toggle_zero_positions()

        main = _prepare_account(
            await ctx.get(portfolio.Portfolio),
            account,
            hide_zero_positions=cookie.hide_zero_positions,
        )

        return self._render_main("main/account.html", main, cookie)

    async def _update_position(self, ctx: handler.Ctx, req: web.Request) -> web.StreamResponse:
        account = domain.AccName(req.match_info["account"])
        ticker = domain.Ticker(req.match_info["ticker"])
        quantity = TypeAdapter(int).validate_python((await req.post()).get("quantity"))

        port = await ctx.get_for_update(portfolio.Portfolio)
        port.update_position(account, ticker, quantity)

        main = _prepare_account(
            port,
            account,
            hide_zero_positions=models.Cookie.from_request(req).hide_zero_positions,
        )

        return self._render_main("main/account.html", main)

    async def _forecast(self, ctx: handler.Ctx, req: web.Request) -> web.StreamResponse:
        async with asyncio.TaskGroup() as tg:
            port_task = tg.create_task(ctx.get(portfolio.Portfolio))
            forecasts_task = tg.create_task(ctx.get(forecasts.Forecast))

        forecast = forecasts_task.result()

        outdated = ""
        poll = False

        if port_task.result().ver != forecast.portfolio_ver:
            outdated = "outdated"
            poll = True

        main = Forecast(
            template="forecast.html",
            card=Card(
                upper=f"Date: {forecast.day} {outdated}",
                main=(f"Mean: {_format_percent(forecast.mean)} / Std: {_format_percent(forecast.std)}"),
                row1=Row(label="Trading interval", value=f"{forecast.forecast_days} days"),
                row2=Row(label="Risk aversion", value=f"{_format_percent(1 - forecast.risk_tolerance)}"),
                row3=Row(label="Forecasts", value=f"{forecast.forecasts_count}"),
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

    async def _optimization(self, ctx: handler.Ctx, req: web.Request) -> web.StreamResponse:
        async with asyncio.TaskGroup() as tg:
            port_task = tg.create_task(ctx.get(portfolio.Portfolio))
            forecasts_task = tg.create_task(ctx.get(forecasts.Forecast))

        forecast = forecasts_task.result()

        outdated = ""
        poll = False

        if port_task.result().ver != forecast.portfolio_ver:
            outdated = "outdated"
            poll = True

        breakeven, buy, sell = forecast.buy_sell()

        main = Optimize(
            template="optimization.html",
            card=Card(
                upper=f"Date: {forecast.day} {outdated}",
                main=(f"Buy tickets: {len(buy)} / Sell tickets: {len(sell)}"),
                row1=Row(label="Trading interval", value=f"{forecast.forecast_days} days"),
                row2=Row(label="Risk aversion", value=f"{_format_percent(1 - forecast.risk_tolerance)}"),
                row3=Row(label="Forecasts", value=f"{forecast.forecasts_count}"),
            ),
            breakeven=breakeven,
            buy=buy,
            sell=sell,
        )

        return await self._render_page(
            ctx,
            "Optimization",
            req,
            main,
            poll=poll,
        )

    async def _dividends(self, ctx: handler.Ctx, req: web.Request) -> web.StreamResponse:
        ticker = domain.UID(req.match_info["ticker"])

        async with asyncio.TaskGroup() as tg:
            raw_task = tg.create_task(ctx.get(raw.DivRaw, ticker))
            reestry_task = tg.create_task(ctx.get(reestry.DivReestry, ticker))

        raw_div = await raw_task
        reestry_div = await reestry_task

        return await self._render_page(
            ctx,
            ticker,
            req,
            _prepare_dividends(raw_div, reestry_div),
        )

    async def _dividend_add(self, ctx: handler.Ctx, req: web.Request) -> web.StreamResponse:
        ticker = domain.UID(req.match_info["ticker"])

        async with asyncio.TaskGroup() as tg:
            raw_task = tg.create_task(ctx.get_for_update(raw.DivRaw, ticker))
            reestry_task = tg.create_task(ctx.get(reestry.DivReestry, ticker))
            status_task = tg.create_task(ctx.get_for_update(status.DivStatus))

        raw_div = await raw_task
        reestry_div = await reestry_task
        status_div = await status_task

        day = TypeAdapter(date).validate_python((await req.post()).get("day"))
        dividend_str = TypeAdapter(str).validate_python((await req.post()).get("dividend"))
        dividend = TypeAdapter(float).validate_python(dividend_str.replace(" ", "").replace(",", "."))

        raw_div.add_row(raw.Row(day=day, dividend=dividend))
        status_div.filter(raw_div)

        return self._render_main("main/dividends.html", _prepare_dividends(raw_div, reestry_div))

    async def _dividend_remove(self, ctx: handler.Ctx, req: web.Request) -> web.StreamResponse:
        ticker = domain.UID(req.match_info["ticker"])

        async with asyncio.TaskGroup() as tg:
            raw_task = tg.create_task(ctx.get_for_update(raw.DivRaw, ticker))
            reestry_task = tg.create_task(ctx.get(reestry.DivReestry, ticker))

        raw_div = await raw_task
        reestry_div = await reestry_task

        day = TypeAdapter(date).validate_python((await req.post()).get("day"))
        dividend_str = TypeAdapter(str).validate_python((await req.post()).get("dividend"))
        dividend = TypeAdapter(float).validate_python(dividend_str.replace(" ", "").replace(",", "."))

        raw_div.remove_row(raw.Row(day=day, dividend=dividend))

        return self._render_main("main/dividends.html", _prepare_dividends(raw_div, reestry_div))

    async def _settings(self, ctx: handler.Ctx, req: web.Request) -> web.StreamResponse:
        port = await ctx.get(portfolio.Portfolio)

        main = Settings(
            template="settings.html",
            hide_accounts_zero_positions=models.Cookie.from_request(req).hide_zero_positions,
            accounts=sorted(port.account_names),
            exclude=sorted(port.exclude),
        )

        return await self._render_page(
            ctx,
            "Settings",
            req,
            main,
        )

    async def _hide_zero_positions(self, ctx: handler.Ctx, req: web.Request) -> web.StreamResponse:  # noqa: ARG002
        cookie = models.Cookie.from_request(req)
        cookie.hide_zero_positions = (await req.post()).get("hide") is not None

        return _with_cookie(web.Response(status=http.HTTPStatus.NO_CONTENT), cookie)

    async def _create_acount(self, ctx: handler.Ctx, req: web.Request) -> web.StreamResponse:
        account = TypeAdapter(str).validate_python((await req.post()).get("account"))
        if account != parse.quote(account):
            raise errors.ControllersError("Invalid account name - use only english letters and numbers")

        cookie = models.Cookie.from_request(req)

        port = await ctx.get_for_update(portfolio.Portfolio)
        port.create_acount(domain.AccName(account))

        main = Settings(
            template="settings.html",
            hide_accounts_zero_positions=cookie.hide_zero_positions,
            accounts=sorted(port.account_names),
            exclude=sorted(port.exclude),
        )

        return await self._render_page(
            ctx,
            "Settings",
            req,
            main,
        )

    async def _remove_acount(self, ctx: handler.Ctx, req: web.Request) -> web.StreamResponse:
        account = domain.AccName(req.match_info["account"])
        cookie = models.Cookie.from_request(req)

        port = await ctx.get_for_update(portfolio.Portfolio)
        port.remove_acount(account)

        main = Settings(
            template="settings.html",
            hide_accounts_zero_positions=cookie.hide_zero_positions,
            accounts=sorted(port.account_names),
            exclude=sorted(port.exclude),
        )

        return await self._render_page(
            ctx,
            "Settings",
            req,
            main,
        )

    async def _not_exclude_ticker(self, ctx: handler.Ctx, req: web.Request) -> web.StreamResponse:
        ticker = TypeAdapter(str).validate_python(req.match_info["ticker"])
        cookie = models.Cookie.from_request(req)

        port = await ctx.get_for_update(portfolio.Portfolio)
        port.not_exclude_ticker(domain.Ticker(ticker.upper()))

        main = Settings(
            template="settings.html",
            hide_accounts_zero_positions=cookie.hide_zero_positions,
            accounts=sorted(port.account_names),
            exclude=sorted(port.exclude),
        )

        return self._render_main("main/settings.html", main)

    async def _exclude_ticker(self, ctx: handler.Ctx, req: web.Request) -> web.StreamResponse:
        ticker = TypeAdapter(str).validate_python((await req.post()).get("ticker"))
        cookie = models.Cookie.from_request(req)

        port = await ctx.get_for_update(portfolio.Portfolio)
        port.exclude_ticker(domain.Ticker(ticker.upper()))

        main = Settings(
            template="settings.html",
            hide_accounts_zero_positions=cookie.hide_zero_positions,
            accounts=sorted(port.account_names),
            exclude=sorted(port.exclude),
        )

        return self._render_main("main/settings.html", main)

    async def _theme(self, ctx: handler.Ctx, req: web.Request) -> web.StreamResponse:
        theme = req.match_info["theme"]

        if theme not in models.Theme:
            return web.HTTPNotFound(text=f"Invalid theme - {theme}")

        cookie = models.Cookie.from_request(req)
        cookie.theme = models.Theme(theme)

        return self._render_theme(cookie)

    def _render_theme(self, cookie: models.Cookie) -> web.StreamResponse:
        return _with_cookie(
            web.Response(
                text=self._env.get_template(f"theme/{cookie.theme}.html").render(),
                content_type="text/html",
            ),
            cookie,
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
        cookie = models.Cookie.from_request(req)

        async with asyncio.TaskGroup() as tg:
            port_task = tg.create_task(ctx.get(portfolio.Portfolio))
            div_task = tg.create_task(ctx.get(status.DivStatus))

        layout = Layout(
            title=title,
            selected_path=req.path,
            poll=poll,
            theme=cookie.theme,
            accounts=sorted(port_task.result().account_names),
            dividends=sorted({row.ticker for row in div_task.result().df}),
        )

        match req.headers.get("HX-Request") == "true":
            case True:
                template = "body.html"
            case False:
                template = "index.html"

        return web.Response(
            text=self._env.get_template(template).render(
                layout=layout,
                main=main,
                format_float=_format_float,
                format_percent=_format_percent,
            ),
            content_type="text/html",
        )

    def _render_main(
        self,
        template: str,
        main: Any,
        cookie: models.Cookie | None = None,
    ) -> web.StreamResponse:
        return _with_cookie(
            web.Response(
                text=self._env.get_template(template).render(
                    main=main,
                    format_float=_format_float,
                    format_percent=_format_percent,
                ),
                content_type="text/html",
            ),
            cookie,
        )

    @web.middleware
    async def _alerts_middleware(
        self,
        request: web.Request,
        handler: typedefs.Handler,
    ) -> web.StreamResponse:
        code = http.HTTPStatus.INTERNAL_SERVER_ERROR
        error: Exception | None = None

        try:
            return await handler(request)
        except* (errors.AdapterError, errors.ControllersError) as err:
            code = http.HTTPStatus.INTERNAL_SERVER_ERROR
            error = err.exceptions[0]

        except* ValidationError as err:
            code = http.HTTPStatus.BAD_REQUEST
            error = errors.ControllersError(
                _get_first_exception(err).errors()[0]["msg"],
            )

        except* (errors.DomainError, errors.UseCasesError) as err:
            code = http.HTTPStatus.BAD_REQUEST
            error = err.exceptions[0]

        except* web.HTTPNotFound as err:
            code = http.HTTPStatus.NOT_FOUND
            error = err.exceptions[0]

        self._lgr.warning("Can't handle request - %s", error)

        return self._render_alert(code, f"{error.__class__.__name__}: {error}")

    def _render_alert(self, code: int, alert: str) -> web.Response:
        return web.Response(
            status=code,
            text=self._env.get_template("components/alert.html").render(alert=alert),
            content_type="text/html",
        )

    async def _static_file(self, req: web.Request) -> web.StreamResponse:
        file_path = Path(__file__).parent / "static" / req.match_info["path"]

        return web.FileResponse(file_path)


def _prepare_dividends(raw_div: raw.DivRaw, reestry_div: reestry.DivReestry) -> Dividends:
    compare = [
        DivRow(
            day=row_source.day,
            dividend=row_source.dividend,
            status=DivStatus.MISSED,
        )
        for row_source in reestry_div.df
        if not raw_div.has_row(raw.Row(day=row_source.day, dividend=row_source.dividend))
    ]

    for raw_row in raw_div.df:
        row_status = DivStatus.EXTRA
        if reestry_div.has_row(raw_row):
            row_status = DivStatus.OK

        compare.append(
            DivRow(
                day=raw_row.day,
                dividend=raw_row.dividend,
                status=row_status,
            ),
        )

    compare.sort(key=lambda compare: compare.to_tuple())

    return Dividends(
        template="dividends.html",
        ticker=raw_div.uid,
        dividends=compare,
    )


def _get_first_exception(exc: ExceptionGroup[ValidationError] | ValidationError) -> ValidationError:
    if isinstance(exc, ValidationError):
        return exc

    return _get_first_exception(exc.exceptions[0])


def _prepare_account(
    portfolio: portfolio.Portfolio,
    account: domain.AccName,
    *,
    hide_zero_positions: bool,
) -> Account:
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

    return Account(
        template="account.html",
        account=account,
        card=Card(
            upper=f"Date: {portfolio.day}",
            main=f"Value: {_format_float(value, 0)} ₽",
            row1=Row(label="Share of portfolio", value=f"{_format_percent(value / portfolio.value())}"),
            row2=Row(label="Open positions", value=f"{portfolio.open_positions(account)}"),
            row3=Row(label="Total positions", value=f"{_format_float(len(portfolio.positions), 0)}"),
        ),
        value=value,
        cash=portfolio.cash_value(account),
        positions=positions,
    )


def _format_float(number: float, decimals: int | None = None) -> str:
    match decimals:
        case None if number % 1:
            rez = f"{number:_}"
        case None:
            rez = f"{int(number):_}"
        case _:
            rez = f"{number:_.{decimals}f}"

    return rez.replace("_", " ").replace(".", ",")


def _format_percent(number: float) -> str:
    return f"{_format_float(number * 100, 1)} %"


def _with_cookie(resp: web.Response, cookie: models.Cookie | None) -> web.Response:
    if cookie:
        for name, value in cookie:
            resp.set_cookie(
                name,
                value,
                max_age=_YEAR_IN_SECONDS,
                httponly=True,
                samesite="Lax",
            )

    return resp
