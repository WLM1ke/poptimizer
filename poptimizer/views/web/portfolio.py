import asyncio
import http
import logging
from enum import StrEnum, auto
from pathlib import Path
from typing import Any
from urllib import parse

from aiohttp import typedefs, web
from jinja2 import Environment, FileSystemLoader, select_autoescape
from pydantic import BaseModel, Field, TypeAdapter, ValidationError

from poptimizer import errors
from poptimizer.controllers.bus import msg
from poptimizer.domain import domain, settings
from poptimizer.domain.div import raw, reestry, status
from poptimizer.domain.domain import AccName, Ticker, date
from poptimizer.domain.portfolio import forecasts, portfolio
from poptimizer.use_cases import handler


class Layout(BaseModel):
    title: str
    path: str
    poll: bool
    theme: settings.Theme
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


class Handlers:
    def __init__(self, app: web.Application, bus: msg.Bus) -> None:
        self._lgr = logging.getLogger()
        self._bus = bus
        self._env = Environment(
            loader=FileSystemLoader(Path(__file__).parent / "templates"),
            autoescape=select_autoescape(["html"]),
        )

        app.middlewares.append(self._alerts_middleware)

        routes = (
            (
                web.get,
                "/",
                self.portfolio,
            ),
            (
                web.get,
                "/accounts/{account}",
                self.account,
            ),
            (
                web.patch,
                "/accounts/{account}/{ticker}",
                self.update_position,
            ),
            (
                web.get,
                "/forecast",
                self.forecast,
            ),
            (
                web.get,
                "/optimization",
                self.optimization,
            ),
            (
                web.get,
                "/dividends/{ticker}",
                self.dividends,
            ),
            (
                web.patch,
                "/dividends/{ticker}/add",
                self.dividend_add,
            ),
            (
                web.patch,
                "/dividends/{ticker}/remove",
                self.dividend_remove,
            ),
            (
                web.get,
                "/settings",
                self.settings,
            ),
            (
                web.patch,
                "/settings/hide_zero_positions",
                self.hide_zero_positions,
            ),
            (
                web.post,
                "/accounts",
                self.create_acount,
            ),
            (
                web.delete,
                "/accounts/{account}",
                self.remove_acount,
            ),
            (
                web.post,
                "/exclude",
                self.exclude_ticker,
            ),
            (
                web.delete,
                "/exclude/{ticker}",
                self.not_exclude_ticker,
            ),
            (
                web.patch,
                "/theme/{theme}",
                self.theme,
            ),
        )

        for method, path, unwrapped_handler in routes:
            app.add_routes([method(path, bus.wrap(unwrapped_handler))])

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

    async def account(self, ctx: handler.Ctx, req: web.Request) -> web.StreamResponse:
        account = domain.AccName(req.match_info["account"])

        async with asyncio.TaskGroup() as tg:
            port_task = tg.create_task(ctx.get(portfolio.Portfolio))
            settings_task = tg.create_task(ctx.get(settings.Settings))

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
            settings_task = tg.create_task(ctx.get(settings.Settings))

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

    async def optimization(self, ctx: handler.Ctx, req: web.Request) -> web.StreamResponse:
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

    async def dividends(self, ctx: handler.Ctx, req: web.Request) -> web.StreamResponse:
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
            self._prepare_dividends(raw_div, reestry_div),
        )

    def _prepare_dividends(self, raw_div: raw.DivRaw, reestry_div: reestry.DivReestry) -> Dividends:
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

    async def dividend_add(self, ctx: handler.Ctx, req: web.Request) -> web.StreamResponse:
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

        return web.Response(
            text=self._env.get_template("main/dividends.html").render(
                main=self._prepare_dividends(raw_div, reestry_div),
                format_float=_format_float,
                format_percent=_format_percent,
            ),
            content_type="text/html",
        )

    async def dividend_remove(self, ctx: handler.Ctx, req: web.Request) -> web.StreamResponse:
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

        return web.Response(
            text=self._env.get_template("main/dividends.html").render(
                main=self._prepare_dividends(raw_div, reestry_div),
                format_float=_format_float,
                format_percent=_format_percent,
            ),
            content_type="text/html",
        )

    async def settings(self, ctx: handler.Ctx, req: web.Request) -> web.StreamResponse:
        async with asyncio.TaskGroup() as tg:
            settings_task = tg.create_task(ctx.get(settings.Settings))
            port_task = tg.create_task(ctx.get(portfolio.Portfolio))

        main = Settings(
            template="settings.html",
            hide_accounts_zero_positions=settings_task.result().hide_zero_positions,
            accounts=sorted(port_task.result().account_names),
            exclude=sorted(port_task.result().exclude),
        )

        return await self._render_page(
            ctx,
            "Settings",
            req,
            main,
        )

    async def hide_zero_positions(self, ctx: handler.Ctx, req: web.Request) -> web.StreamResponse:
        current_settings = await ctx.get_for_update(settings.Settings)

        hide = (await req.post()).get("hide") is not None
        current_settings.update_hide_zero_positions(hide=hide)

        return web.Response(status=http.HTTPStatus.NO_CONTENT)

    async def create_acount(self, ctx: handler.Ctx, req: web.Request) -> web.StreamResponse:
        account = TypeAdapter(str).validate_python((await req.post()).get("account"))
        if account != parse.quote(account):
            raise errors.ControllersError("Invalid account name - use only english letters and numbers")

        async with asyncio.TaskGroup() as tg:
            settings_task = tg.create_task(ctx.get(settings.Settings))
            port_task = tg.create_task(ctx.get_for_update(portfolio.Portfolio))

        port_task.result().create_acount(domain.AccName(account))

        main = Settings(
            template="settings.html",
            hide_accounts_zero_positions=settings_task.result().hide_zero_positions,
            accounts=sorted(port_task.result().account_names),
            exclude=sorted(port_task.result().exclude),
        )

        return await self._render_page(
            ctx,
            "Settings",
            req,
            main,
        )

    async def remove_acount(self, ctx: handler.Ctx, req: web.Request) -> web.StreamResponse:
        account = domain.AccName(req.match_info["account"])

        async with asyncio.TaskGroup() as tg:
            settings_task = tg.create_task(ctx.get(settings.Settings))
            port_task = tg.create_task(ctx.get_for_update(portfolio.Portfolio))

        port_task.result().remove_acount(account)

        main = Settings(
            template="settings.html",
            hide_accounts_zero_positions=settings_task.result().hide_zero_positions,
            accounts=sorted(port_task.result().account_names),
            exclude=sorted(port_task.result().exclude),
        )

        return await self._render_page(
            ctx,
            "Settings",
            req,
            main,
        )

    async def not_exclude_ticker(self, ctx: handler.Ctx, req: web.Request) -> web.StreamResponse:
        ticker = TypeAdapter(str).validate_python(req.match_info["ticker"])

        async with asyncio.TaskGroup() as tg:
            settings_task = tg.create_task(ctx.get(settings.Settings))
            port_task = tg.create_task(ctx.get_for_update(portfolio.Portfolio))

        port_task.result().not_exclude_ticker(domain.Ticker(ticker.upper()))

        main = Settings(
            template="settings.html",
            hide_accounts_zero_positions=settings_task.result().hide_zero_positions,
            accounts=sorted(port_task.result().account_names),
            exclude=sorted(port_task.result().exclude),
        )

        return web.Response(
            text=self._env.get_template("main/settings.html").render(
                main=main,
                format_float=_format_float,
                format_percent=_format_percent,
            ),
            content_type="text/html",
        )

    async def exclude_ticker(self, ctx: handler.Ctx, req: web.Request) -> web.StreamResponse:
        ticker = TypeAdapter(str).validate_python((await req.post()).get("ticker"))

        async with asyncio.TaskGroup() as tg:
            settings_task = tg.create_task(ctx.get(settings.Settings))
            port_task = tg.create_task(ctx.get_for_update(portfolio.Portfolio))

        port_task.result().exclude_ticker(domain.Ticker(ticker.upper()))

        main = Settings(
            template="settings.html",
            hide_accounts_zero_positions=settings_task.result().hide_zero_positions,
            accounts=sorted(port_task.result().account_names),
            exclude=sorted(port_task.result().exclude),
        )

        return web.Response(
            text=self._env.get_template("main/settings.html").render(
                main=main,
                format_float=_format_float,
                format_percent=_format_percent,
            ),
            content_type="text/html",
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
            settings_task = tg.create_task(ctx.get(settings.Settings))
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

    async def theme(self, ctx: handler.Ctx, req: web.Request) -> web.StreamResponse:
        theme = req.match_info["theme"]

        if theme not in settings.Theme:
            return web.HTTPNotFound(text=f"Invalid theme - {theme}")

        current_settings = await ctx.get_for_update(settings.Settings)
        current_settings.update_theme(settings.Theme(theme))

        return web.Response(
            text=self._env.get_template(f"theme/{theme}.html").render(),
            content_type="text/html",
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

        return self._alert(code, f"{error.__class__.__name__}: {error}")

    def _alert(self, code: int, alert: str) -> web.Response:
        return web.Response(
            status=code,
            text=self._env.get_template("components/alert.html").render(alert=alert),
            content_type="text/html",
        )

    async def static_file(self, req: web.Request) -> web.StreamResponse:
        file_path = Path(__file__).parent / "static" / req.match_info["path"]

        return web.FileResponse(file_path)


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
        cash=portfolio.cash_value(),
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
