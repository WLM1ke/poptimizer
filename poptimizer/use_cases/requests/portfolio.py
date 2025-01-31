import sys
from datetime import date
from typing import Final, Self

from pydantic import BaseModel, NonNegativeInt, PositiveFloat, PositiveInt

from poptimizer.domain import domain
from poptimizer.domain.portfolio import forecasts, portfolio
from poptimizer.use_cases import handler

_MAX_FLOAT: Final = sys.float_info.max


class GetPortfolio(handler.DTO): ...


class CreateAccount(handler.DTO):
    account: domain.AccName


class RemoveAccount(handler.DTO):
    account: domain.AccName


class Security(BaseModel):
    lot: PositiveInt
    price: PositiveFloat


class Portfolio(handler.DTO):
    day: date
    ver: int
    account_names: list[domain.AccName]
    cash: portfolio.AccountData
    positions: list[portfolio.Position]

    @classmethod
    def from_portfolio(cls, port: portfolio.Portfolio) -> Self:
        return cls(
            day=port.day,
            ver=port.ver,
            account_names=sorted(port.account_names),
            cash=port.cash,
            positions=port.positions,
        )

    @classmethod
    def from_updated_portfolio(cls, port: portfolio.Portfolio) -> Self:
        return cls(
            day=port.day,
            ver=port.ver + 1,
            account_names=sorted(port.account_names),
            cash=port.cash,
            positions=port.positions,
        )


class Position(handler.DTO):
    account: domain.AccName
    ticker: domain.Ticker
    amount: NonNegativeInt


class GetForecast(handler.DTO): ...


def _remove_inf_grad(pos: forecasts.Position) -> forecasts.Position:
    pos.grad_upper = min(_MAX_FLOAT, pos.grad_upper)
    pos.grad_lower = max(-_MAX_FLOAT, pos.grad_lower)

    return pos


class Forecast(handler.DTO):
    day: date
    portfolio_ver: int
    mean: float = 0
    std: float = 0
    positions: list[forecasts.Position]
    forecasts_count: int
    forecast_days: int
    risk_tolerance: float

    @classmethod
    def from_forecast(cls, forecast: forecasts.Forecast) -> Self:
        return cls(
            day=forecast.day,
            portfolio_ver=forecast.portfolio_ver,
            mean=forecast.mean,
            std=forecast.std,
            positions=[_remove_inf_grad(pos) for pos in forecast.positions],
            forecasts_count=forecast.forecasts_count,
            forecast_days=forecast.forecast_days,
            risk_tolerance=forecast.risk_tolerance,
        )


class PortfolioHandler:
    async def get_portfolio(self, ctx: handler.Ctx, msg: GetPortfolio) -> Portfolio:  # noqa: ARG002
        port = await ctx.get(portfolio.Portfolio)

        return Portfolio.from_portfolio(port)

    async def create_account(self, ctx: handler.Ctx, msg: CreateAccount) -> Portfolio:
        port = await ctx.get_for_update(portfolio.Portfolio)

        port.create_acount(msg.account)

        return Portfolio.from_updated_portfolio(port)

    async def remove_acount(self, ctx: handler.Ctx, msg: RemoveAccount) -> Portfolio:
        port = await ctx.get_for_update(portfolio.Portfolio)

        port.remove_acount(msg.account)

        return Portfolio.from_updated_portfolio(port)

    async def update_position(self, ctx: handler.Ctx, msg: Position) -> Portfolio:
        port = await ctx.get_for_update(portfolio.Portfolio)

        port.update_position(msg.account, msg.ticker, msg.amount)

        return Portfolio.from_updated_portfolio(port)

    async def get_forecast(self, ctx: handler.Ctx, msg: GetForecast) -> Forecast:  # noqa: ARG002
        forecast = await ctx.get(forecasts.Forecast)

        return Forecast.from_forecast(forecast)
