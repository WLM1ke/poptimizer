import asyncio
import http
import logging
from collections.abc import Awaitable, Callable
from contextlib import AbstractAsyncContextManager
from datetime import date
from pathlib import Path

from aiohttp import typedefs, web
from pydantic import TypeAdapter, ValidationError

from poptimizer.core import domain, errors
from poptimizer.data.div import raw, status
from poptimizer.forecast.models import forecasts
from poptimizer.portfolio.models import portfolio
from poptimizer.portfolio.models.settings import Settings
from poptimizer.runtime import uow
from poptimizer.views.web import models, view


class _UOWHandler:
    def __init__(
        self,
        handler: Callable[[uow.Repo, web.Request], Awaitable[web.StreamResponse]],
        uow_factory: Callable[[], AbstractAsyncContextManager[uow.Repo]],
    ) -> None:
        self._handler = handler
        self._uow_factory = uow_factory

    async def __call__(self, req: web.Request) -> web.StreamResponse:
        async with self._uow_factory() as repo:
            return await self._handler(repo, req)


class App(web.Application):
    def __init__(
        self,
        lgr: logging.Logger,
        uow_factory: Callable[[], AbstractAsyncContextManager[uow.Repo]],
    ) -> None:
        super().__init__(middlewares=[self._alerts_middleware])
        self._lgr = lgr
        self._render = view.View()
        self._uow_factory = uow_factory

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

        for method, path, handler in routes:
            self.add_routes([method(path, _UOWHandler(handler, self._uow_factory))])

        self.add_routes([web.get("/{path:.*}", self._static_file)])

    async def _portfolio(self, repo: uow.Repo, req: web.Request) -> web.StreamResponse:
        port = await repo.get(portfolio.Portfolio)

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
            repo,
            req,
            main,
        )

    async def _account(self, repo: uow.Repo, req: web.Request) -> web.StreamResponse:
        account = domain.AccName(req.match_info["account"])
        cookie = models.Cookie.from_request(req)

        main = _prepare_account(
            await repo.get(portfolio.Portfolio),
            account,
            hide_zero_positions=cookie.hide_zero_positions,
        )

        return await self._render_page(
            repo,
            req,
            main,
        )

    async def _account_toggle_positions(self, repo: uow.Repo, req: web.Request) -> web.StreamResponse:
        account = domain.AccName(req.match_info["account"])
        cookie = models.Cookie.from_request(req)

        cookie.toggle_zero_positions()

        main = _prepare_account(
            await repo.get(portfolio.Portfolio),
            account,
            hide_zero_positions=cookie.hide_zero_positions,
        )

        return self._render.render_main(main, cookie)

    async def _forecast(self, repo: uow.Repo, req: web.Request) -> web.StreamResponse:
        forecast = await repo.get(forecasts.Forecast)

        card = models.Card(
            upper=f"Date: {forecast.day}",
            main=(f"Mean: {view.format_percent(forecast.mean)} / Std: {view.format_percent(forecast.std)}"),
            row1=models.Row(label="Trading interval", value=f"{forecast.forecast_days} days"),
            row2=models.Row(label="Risk aversion", value=f"{view.format_percent(1 - forecast.risk_tolerance)}"),
            row3=models.Row(label="Forecasts", value=f"{forecast.forecasts_cnt}"),
        )

        main = models.Forecast(
            card=card,
            positions=forecast.positions,
        )

        return await self._render_page(
            repo,
            req,
            main,
        )

    async def _optimization(self, repo: uow.Repo, req: web.Request) -> web.StreamResponse:
        forecast = await repo.get(forecasts.Forecast)
        port = await repo.get(portfolio.Portfolio)
        settings = await repo.get(Settings)

        breakeven, buy, sell = forecast.buy_sell(port.illiquid | settings.exclude)

        card = models.Card(
            upper=f"Date: {forecast.day}",
            main=(f"Mean: {view.format_percent(forecast.mean)} / Std: {view.format_percent(forecast.std)}"),
            row1=models.Row(label="Trading interval", value=f"{forecast.forecast_days} days"),
            row2=models.Row(label="Risk aversion", value=f"{view.format_percent(1 - forecast.risk_tolerance)}"),
            row3=models.Row(label="Forecasts", value=f"{forecast.forecasts_cnt}"),
        )

        main = models.Optimize(
            card=card,
            breakeven=breakeven,
            buy=buy,
            sell=sell,
        )

        return await self._render_page(
            repo,
            req,
            main,
        )

    async def _dividends(self, repo: uow.Repo, req: web.Request) -> web.StreamResponse:
        ticker = domain.UID(req.match_info["ticker"])

        async with asyncio.TaskGroup() as tg:
            raw_task = tg.create_task(repo.get(raw.DivRaw, ticker))
            reestry_task = tg.create_task(repo.get(raw.DivReestry, ticker))

        return await self._render_page(
            repo,
            req,
            _prepare_dividends(await raw_task, await reestry_task),
        )

    async def _dividend_add(self, repo: uow.Repo, req: web.Request) -> web.StreamResponse:
        ticker = domain.UID(req.match_info["ticker"])

        async with asyncio.TaskGroup() as tg:
            raw_task = tg.create_task(repo.get_for_update(raw.DivRaw, ticker))
            reestry_task = tg.create_task(repo.get(raw.DivReestry, ticker))
            status_task = tg.create_task(repo.get_for_update(status.DivStatus))

        raw_div = await raw_task
        reestry_div = await reestry_task
        status_div = await status_task

        day = TypeAdapter(date).validate_python((await req.post()).get("day"))
        dividend_str = TypeAdapter(str).validate_python((await req.post()).get("dividend"))
        dividend = TypeAdapter(float).validate_python(dividend_str.replace(" ", "").replace(",", "."))

        raw_div.add_row(raw.Row(day=day, dividend=dividend))
        status_div.filter(raw_div)

        return self._render.render_main(_prepare_dividends(raw_div, reestry_div))

    async def _dividend_remove(self, repo: uow.Repo, req: web.Request) -> web.StreamResponse:
        ticker = domain.UID(req.match_info["ticker"])

        async with asyncio.TaskGroup() as tg:
            raw_task = tg.create_task(repo.get_for_update(raw.DivRaw, ticker))
            reestry_task = tg.create_task(repo.get(raw.DivReestry, ticker))

        raw_div = await raw_task
        reestry_div = await reestry_task

        day = TypeAdapter(date).validate_python((await req.post()).get("day"))
        dividend_str = TypeAdapter(str).validate_python((await req.post()).get("dividend"))
        dividend = TypeAdapter(float).validate_python(dividend_str.replace(" ", "").replace(",", "."))

        raw_div.remove_row(raw.Row(day=day, dividend=dividend))

        return self._render.render_main(_prepare_dividends(raw_div, reestry_div))

    async def _settings(self, repo: uow.Repo, req: web.Request) -> web.StreamResponse:
        return await self._render_page(
            repo,
            req,
            await self._settings_page(repo, req),
        )

    async def _hide_zero_positions(self, _repo: uow.Repo, req: web.Request) -> web.StreamResponse:
        cookie = models.Cookie.from_request(req)
        cookie.hide_zero_positions = (await req.post()).get("hide") is not None

        return self._render.set_cookie(cookie)

    async def _not_exclude_ticker(self, repo: uow.Repo, req: web.Request) -> web.StreamResponse:
        ticker = domain.Ticker(TypeAdapter(str).validate_python(req.match_info["ticker"]).upper())
        settings = await repo.get_for_update(Settings)

        if ticker not in settings.exclude:
            raise errors.DomainError(f"ticker {ticker} is not excluded")

        settings.exclude.remove(ticker)

        return self._render.render_main(await self._settings_page(repo, req))

    async def _exclude_ticker(self, repo: uow.Repo, req: web.Request) -> web.StreamResponse:
        ticker = domain.Ticker(TypeAdapter(str).validate_python((await req.post()).get("ticker")).upper())
        port = await repo.get(portfolio.Portfolio)

        if ticker not in port.tickers:
            raise errors.DomainError(f"ticker {ticker} is not in portfolio")

        settings = await repo.get_for_update(Settings)
        settings.exclude.add(ticker)

        return self._render.render_main(await self._settings_page(repo, req))

    async def _theme(self, _repo: uow.Repo, req: web.Request) -> web.StreamResponse:
        theme = req.match_info["theme"]

        if theme not in models.Theme:
            return web.HTTPNotFound(text=f"Invalid theme - {theme}")

        cookie = models.Cookie.from_request(req)
        cookie.theme = models.Theme(theme)

        return self._render.render_theme(cookie)

    async def _settings_page(self, repo: uow.Repo, req: web.Request) -> models.Settings:
        settings = await repo.get(Settings)

        return models.Settings(
            hide_accounts_zero_positions=models.Cookie.from_request(req).hide_zero_positions,
            exclude=sorted(settings.exclude),
        )

    async def _render_page(
        self,
        repo: uow.Repo,
        req: web.Request,
        main: models.BasePage,
    ) -> web.StreamResponse:
        async with asyncio.TaskGroup() as tg:
            port_task = tg.create_task(repo.get(portfolio.Portfolio))
            div_task = tg.create_task(repo.get(status.DivStatus))

        layout = models.Layout(
            selected_path=req.path,
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


def _prepare_dividends(raw_div: raw.DivRaw, reestry_div: raw.DivReestry) -> models.Dividends:
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
        row1=models.Row(label="Share of portfolio", value=f"{view.format_percent(value / (portfolio.value() or 1))}"),
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
