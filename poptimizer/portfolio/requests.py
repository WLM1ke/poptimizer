from pydantic import NonNegativeInt

from poptimizer.core import domain
from poptimizer.portfolio import portfolio


class PortfolioData(domain.Response):
    day: domain.Day
    accounts: dict[portfolio.AccName, portfolio.Account]
    securities: dict[domain.Ticker, portfolio.Security]


class GetPortfolio(domain.Request[PortfolioData]):
    ...


class PortfolioDataRequestHandler:
    async def handle(self, ctx: domain.Ctx, request: GetPortfolio) -> PortfolioData:  # noqa: ARG002
        port = await ctx.get(portfolio.Portfolio, for_update=False)

        return PortfolioData(
            day=port.day,
            accounts=port.accounts,
            securities=port.securities,
        )


class CreateAccount(domain.Request[PortfolioData]):
    name: str


class CreateAccountRequestHandler:
    async def handle(self, ctx: domain.Ctx, request: CreateAccount) -> PortfolioData:
        port = await ctx.get(portfolio.Portfolio)

        port.create_acount(portfolio.AccName(request.name))

        return PortfolioData(
            day=port.day,
            accounts=port.accounts,
            securities=port.securities,
        )


class RemoveAccount(domain.Request[PortfolioData]):
    name: str


class RemoveAccountRequestHandler:
    async def handle(self, ctx: domain.Ctx, request: RemoveAccount) -> PortfolioData:
        port = await ctx.get(portfolio.Portfolio)

        port.remove_acount(portfolio.AccName(request.name))

        return PortfolioData(
            day=port.day,
            accounts=port.accounts,
            securities=port.securities,
        )


class UpdatePosition(domain.Request[PortfolioData]):
    name: str
    ticker: str
    amount: NonNegativeInt


class UpdatePositionRequestHandler:
    async def handle(self, ctx: domain.Ctx, request: UpdatePosition) -> PortfolioData:
        port = await ctx.get(portfolio.Portfolio)

        port.update_position(
            portfolio.AccName(request.name),
            domain.Ticker(request.ticker),
            request.amount,
        )

        ctx.publish(port.get_update_event())

        return PortfolioData(
            day=port.day,
            accounts=port.accounts,
            securities=port.securities,
        )
