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
