from aiohttp import web

from poptimizer.core import domain
from poptimizer.portfolio import contracts


class Views:
    def __init__(self, app: web.Application, ctx: domain.SrvCtx) -> None:
        self._ctx = ctx

        app.add_routes([web.get("/portfolio", self.get_portfolio)])
        app.add_routes([web.post("/portfolio/{account}", self.create_acount)])
        app.add_routes([web.delete("/portfolio/{account}", self.remove_acount)])
        app.add_routes([web.post("/portfolio/{account}/{ticker}", self.update_position)])

    async def get_portfolio(self, request: web.Request) -> web.StreamResponse:  # noqa: ARG002
        portfolio = await self._ctx.request(contracts.GetPortfolio())

        return web.json_response(text=portfolio.model_dump_json())

    async def create_acount(self, request: web.Request) -> web.StreamResponse:
        account = request.match_info["account"]
        portfolio = await self._ctx.request(contracts.CreateAccount(name=account))

        return web.json_response(text=portfolio.model_dump_json())

    async def remove_acount(self, request: web.Request) -> web.StreamResponse:
        account = request.match_info["account"]
        portfolio = await self._ctx.request(contracts.RemoveAccount(name=account))

        return web.json_response(text=portfolio.model_dump_json())

    async def update_position(self, request: web.Request) -> web.StreamResponse:
        account = request.match_info["account"]
        ticker = request.match_info["ticker"]
        json = await request.json()
        portfolio = await self._ctx.request(
            contracts.UpdatePosition(
                name=account,
                ticker=ticker,
                amount=json.get("amount"),
            ),
        )

        return web.json_response(text=portfolio.model_dump_json())
