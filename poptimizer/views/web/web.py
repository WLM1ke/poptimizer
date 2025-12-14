import asyncio
import http
import logging
from pathlib import Path
from typing import Any
from urllib import parse

from aiohttp import typedefs, web
from pydantic import TypeAdapter, ValidationError

from poptimizer import errors
from poptimizer.controllers.bus import msg
from poptimizer.domain import domain
from poptimizer.domain.div import raw, reestry, status
from poptimizer.domain.domain import date
from poptimizer.domain.portfolio import forecasts, portfolio
from poptimizer.use_cases import handler
from poptimizer.views.web import models, view


class App(web.Application):
    def __init__(self, bus: msg.Bus) -> None:
        super().__init__(middlewares=[self._alerts_middleware])
        self._lgr = logging.getLogger()
        self._render = view.View()

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
            self.add_routes([method(path, bus.wrap(unwrapped_handler))])

        self.add_routes([web.get("/{path:.*}", self._static_file)])

    async def _portfolio(self, ctx: handler.Ctx, req: web.Request) -> web.StreamResponse:
        port = await ctx.get(portfolio.Portfolio)

        value = port.value()
        positions = [
            models.Position(
                ticker=position.ticker,
                quantity=position.quantity(),
                lot=position.lot,
                price=position.price,
                value=position.value(),
            )
            for position in port.positions
            if position.quantity() > 0
        ]

        card = models.Card(
            upper=f"Date: {port.day}",
            main=f"Value: {view.format_float(value, 0)} ₽",
            row1=models.Row(label="Effective positions", value=f"{view.format_float(port.effective_positions, 0)}"),
            row2=models.Row(label="Open positions", value=f"{port.open_positions()}"),
            row3=models.Row(label="Total positions", value=f"{view.format_float(len(port.positions), 0)}"),
        )

        main = models.Portfolio(
            card=card,
            value=value,
            cash=port.cash_value(),
            positions=sorted(positions, key=lambda x: x.value, reverse=True),
        )

        return await self._render_page(
            ctx,
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

        return self._render.render_main(main, cookie)

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

        return self._render.render_main(main)

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

        card = models.Card(
            upper=f"Date: {forecast.day} {outdated}",
            main=(f"Mean: {view.format_percent(forecast.mean)} / Std: {view.format_percent(forecast.std)}"),
            row1=models.Row(label="Trading interval", value=f"{forecast.forecast_days} days"),
            row2=models.Row(label="Risk aversion", value=f"{view.format_percent(1 - forecast.risk_tolerance)}"),
            row3=models.Row(label="Forecasts", value=f"{forecast.forecasts_count}"),
        )

        main = models.Forecast(
            card=card,
            positions=forecast.positions,
        )

        return await self._render_page(
            ctx,
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

        card = models.Card(
            upper=f"Date: {forecast.day} {outdated}",
            main=(f"Buy tickets: {len(buy)} / Sell tickets: {len(sell)}"),
            row1=models.Row(label="Trading interval", value=f"{forecast.forecast_days} days"),
            row2=models.Row(label="Risk aversion", value=f"{view.format_percent(1 - forecast.risk_tolerance)}"),
            row3=models.Row(label="Forecasts", value=f"{forecast.forecasts_count}"),
        )

        main = models.Optimize(
            card=card,
            breakeven=breakeven,
            buy=buy,
            sell=sell,
        )

        return await self._render_page(
            ctx,
            req,
            main,
            poll=poll,
        )

    async def _dividends(self, ctx: handler.Ctx, req: web.Request) -> web.StreamResponse:
        ticker = domain.UID(req.match_info["ticker"])

        async with asyncio.TaskGroup() as tg:
            raw_task = tg.create_task(ctx.get(raw.DivRaw, ticker))
            reestry_task = tg.create_task(ctx.get(reestry.DivReestry, ticker))

        return await self._render_page(
            ctx,
            req,
            _prepare_dividends(await raw_task, await reestry_task),
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

        return self._render.render_main(_prepare_dividends(raw_div, reestry_div))

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

        return self._render.render_main(_prepare_dividends(raw_div, reestry_div))

    async def _settings(self, ctx: handler.Ctx, req: web.Request) -> web.StreamResponse:
        port = await ctx.get(portfolio.Portfolio)

        main = models.Settings(
            hide_accounts_zero_positions=models.Cookie.from_request(req).hide_zero_positions,
            accounts=sorted(port.account_names),
            exclude=sorted(port.exclude),
        )

        return await self._render_page(
            ctx,
            req,
            main,
        )

    async def _hide_zero_positions(self, ctx: handler.Ctx, req: web.Request) -> web.StreamResponse:  # noqa: ARG002
        cookie = models.Cookie.from_request(req)
        cookie.hide_zero_positions = (await req.post()).get("hide") is not None

        return self._render.set_cookie(cookie)

    async def _create_acount(self, ctx: handler.Ctx, req: web.Request) -> web.StreamResponse:
        account = TypeAdapter(str).validate_python((await req.post()).get("account"))
        if account != parse.quote(account):
            raise errors.ControllersError("Invalid account name - use only english letters and numbers")

        cookie = models.Cookie.from_request(req)

        port = await ctx.get_for_update(portfolio.Portfolio)
        port.create_acount(domain.AccName(account))

        main = models.Settings(
            hide_accounts_zero_positions=cookie.hide_zero_positions,
            accounts=sorted(port.account_names),
            exclude=sorted(port.exclude),
        )

        return await self._render_page(
            ctx,
            req,
            main,
        )

    async def _remove_acount(self, ctx: handler.Ctx, req: web.Request) -> web.StreamResponse:
        account = domain.AccName(req.match_info["account"])
        cookie = models.Cookie.from_request(req)

        port = await ctx.get_for_update(portfolio.Portfolio)
        port.remove_acount(account)

        main = models.Settings(
            hide_accounts_zero_positions=cookie.hide_zero_positions,
            accounts=sorted(port.account_names),
            exclude=sorted(port.exclude),
        )

        return await self._render_page(
            ctx,
            req,
            main,
        )

    async def _not_exclude_ticker(self, ctx: handler.Ctx, req: web.Request) -> web.StreamResponse:
        ticker = TypeAdapter(str).validate_python(req.match_info["ticker"])
        cookie = models.Cookie.from_request(req)

        port = await ctx.get_for_update(portfolio.Portfolio)
        port.not_exclude_ticker(domain.Ticker(ticker.upper()))

        main = models.Settings(
            hide_accounts_zero_positions=cookie.hide_zero_positions,
            accounts=sorted(port.account_names),
            exclude=sorted(port.exclude),
        )

        return self._render.render_main(main)

    async def _exclude_ticker(self, ctx: handler.Ctx, req: web.Request) -> web.StreamResponse:
        ticker = TypeAdapter(str).validate_python((await req.post()).get("ticker"))
        cookie = models.Cookie.from_request(req)

        port = await ctx.get_for_update(portfolio.Portfolio)
        port.exclude_ticker(domain.Ticker(ticker.upper()))

        main = models.Settings(
            hide_accounts_zero_positions=cookie.hide_zero_positions,
            accounts=sorted(port.account_names),
            exclude=sorted(port.exclude),
        )

        return self._render.render_main(main)

    async def _theme(self, ctx: handler.Ctx, req: web.Request) -> web.StreamResponse:  # noqa: ARG002
        theme = req.match_info["theme"]

        if theme not in models.Theme:
            return web.HTTPNotFound(text=f"Invalid theme - {theme}")

        cookie = models.Cookie.from_request(req)
        cookie.theme = models.Theme(theme)

        return self._render.render_theme(cookie)

    async def _render_page(
        self,
        ctx: handler.Ctx,
        req: web.Request,
        main: Any,
        *,
        poll: bool = False,
    ) -> web.StreamResponse:
        async with asyncio.TaskGroup() as tg:
            port_task = tg.create_task(ctx.get(portfolio.Portfolio))
            div_task = tg.create_task(ctx.get(status.DivStatus))

        layout = models.Layout(
            selected_path=req.path,
            poll=poll,
            theme=models.Cookie.from_request(req).theme,
            accounts=sorted(port_task.result().account_names),
            dividends=sorted({row.ticker for row in div_task.result().df}),
        )

        return self._render.render_page(
            layout,
            main,
            first_load=req.headers.get("HX-Request") != "true",
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

        return self._render.render_alert(code, f"{error.__class__.__name__}: {error}")

    async def _static_file(self, req: web.Request) -> web.StreamResponse:
        file_path = Path(__file__).parent / "static" / req.match_info["path"]

        return web.FileResponse(file_path)


def _prepare_dividends(raw_div: raw.DivRaw, reestry_div: reestry.DivReestry) -> models.Dividends:
    compare = [
        models.DivRow(
            day=row_source.day,
            dividend=row_source.dividend,
            status=models.DivStatus.MISSED,
        )
        for row_source in reestry_div.df
        if not raw_div.has_row(raw.Row(day=row_source.day, dividend=row_source.dividend))
    ]

    for raw_row in raw_div.df:
        row_status = models.DivStatus.EXTRA
        if reestry_div.has_row(raw_row):
            row_status = models.DivStatus.OK

        compare.append(
            models.DivRow(
                day=raw_row.day,
                dividend=raw_row.dividend,
                status=row_status,
            ),
        )

    compare.sort(key=lambda compare: compare.to_tuple())

    return models.Dividends(
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
) -> models.Account:
    value = portfolio.value(account)

    positions = [
        models.Position(
            ticker=position.ticker,
            quantity=position.quantity(account),
            lot=position.lot,
            price=position.price,
            value=position.value(account),
        )
        for position in portfolio.positions
        if position.quantity(account) > 0 or not hide_zero_positions
    ]

    card = models.Card(
        upper=f"Date: {portfolio.day}",
        main=f"Value: {view.format_float(value, 0)} ₽",
        row1=models.Row(label="Share of portfolio", value=f"{view.format_percent(value / portfolio.value())}"),
        row2=models.Row(label="Open positions", value=f"{portfolio.open_positions(account)}"),
        row3=models.Row(label="Total positions", value=f"{view.format_float(len(portfolio.positions), 0)}"),
    )

    return models.Account(
        account=account,
        card=card,
        value=value,
        cash=portfolio.cash_value(account),
        positions=positions,
    )
