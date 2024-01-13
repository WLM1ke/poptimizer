from poptimizer.core import domain
from poptimizer.portfolio import portfolio


class PortfolioData(domain.Response):
    timestamp: domain.Day
    ver: domain.Version
    accounts: dict[portfolio.AccName, portfolio.Account]
    securities: dict[portfolio.Ticker, portfolio.Security]


class GetPortfolio(domain.Request[PortfolioData]):
    ...


class PortfolioDataRequestHandler:
    async def handle(self, ctx: domain.Ctx, request: GetPortfolio) -> PortfolioData:  # noqa: ARG002
        port = await ctx.get(portfolio.Portfolio, for_update=False)

        return PortfolioData(
            timestamp=port.timestamp,
            ver=port.ver,
            accounts=port.accounts,
            securities=port.securities,
        )


class CreateAccount(domain.Request[PortfolioData]):
    name: str


class CreateAccountRequestHandler:
    async def handle(self, ctx: domain.Ctx, request: CreateAccount) -> domain.Response:
        port = await ctx.get(portfolio.Portfolio)

        port.create_acount(portfolio.AccName(request.name))

        return PortfolioData(
            timestamp=port.timestamp,
            ver=port.ver,
            accounts=port.accounts,
            securities=port.securities,
        )


class RemoveAccount(domain.Request[PortfolioData]):
    name: str


class RemoveAccountRequestHandler:
    async def handle(self, ctx: domain.Ctx, request: RemoveAccount) -> domain.Response:
        port = await ctx.get(portfolio.Portfolio)

        port.remove_acount(portfolio.AccName(request.name))

        return PortfolioData(
            timestamp=port.timestamp,
            ver=port.ver,
            accounts=port.accounts,
            securities=port.securities,
        )
