from datetime import date
from typing import Self

from pydantic import BaseModel, NonNegativeInt, PositiveFloat, PositiveInt

from poptimizer.domain import domain
from poptimizer.domain.portfolio import portfolio
from poptimizer.use_cases import handler


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
    accounts: dict[domain.AccName, portfolio.Account]
    securities: dict[domain.Ticker, Security]

    @classmethod
    def from_portfolio(cls, port: portfolio.Portfolio) -> Self:
        return cls(
            day=port.day,
            accounts=port.accounts,
            securities={ticker: Security(lot=sec.lot, price=sec.price) for ticker, sec in port.securities.items()},
        )


class Position(handler.DTO):
    account: domain.AccName
    ticker: domain.Ticker
    amount: NonNegativeInt


class PortfolioHandler:
    async def get_portfolio(self, ctx: handler.Ctx, msg: GetPortfolio) -> Portfolio:  # noqa: ARG002
        port = await ctx.get(portfolio.Portfolio)

        return Portfolio.from_portfolio(port)

    async def create_account(self, ctx: handler.Ctx, msg: CreateAccount) -> Portfolio:
        port = await ctx.get_for_update(portfolio.Portfolio)

        port.create_acount(msg.account)

        return Portfolio.from_portfolio(port)

    async def remove_acount(self, ctx: handler.Ctx, msg: RemoveAccount) -> Portfolio:
        port = await ctx.get_for_update(portfolio.Portfolio)

        port.remove_acount(msg.account)

        return Portfolio.from_portfolio(port)

    async def update_position(self, ctx: handler.Ctx, msg: Position) -> Portfolio:
        port = await ctx.get_for_update(portfolio.Portfolio)

        port.update_position(msg.account, msg.ticker, msg.amount)

        return Portfolio.from_portfolio(port)
