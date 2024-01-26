from poptimizer.core import domain
from poptimizer.portfolio import portfolio
from poptimizer.portfolio.contracts import CreateAccount, GetPortfolio, PortfolioData, RemoveAccount, UpdatePosition


class PortfolioDataRequestHandler:
    async def handle(self, ctx: domain.Ctx, request: GetPortfolio) -> PortfolioData:  # noqa: ARG002
        port = await ctx.get(portfolio.Portfolio, for_update=False)

        return PortfolioData(
            day=port.day,
            accounts=port.accounts,
            securities=port.securities,
        )


class CreateAccountRequestHandler:
    async def handle(self, ctx: domain.Ctx, request: CreateAccount) -> PortfolioData:
        port = await ctx.get(portfolio.Portfolio)

        port.create_acount(portfolio.AccName(request.name))

        return PortfolioData(
            day=port.day,
            accounts=port.accounts,
            securities=port.securities,
        )


class RemoveAccountRequestHandler:
    async def handle(self, ctx: domain.Ctx, request: RemoveAccount) -> PortfolioData:
        port = await ctx.get(portfolio.Portfolio)

        port.remove_acount(portfolio.AccName(request.name))

        return PortfolioData(
            day=port.day,
            accounts=port.accounts,
            securities=port.securities,
        )


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
