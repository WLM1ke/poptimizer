from aiohttp import web

from poptimizer.core import domain
from poptimizer.portfolio import contracts


class Views:
    def __init__(self, app: web.Application, ctx: domain.SrvCtx) -> None:
        self._ctx = ctx

        app.add_routes([web.get("/portfolio", self.get)])

    async def get(self, request: web.Request) -> web.StreamResponse:  # noqa: ARG002
        portfolio = await self._ctx.request(contracts.GetPortfolio())

        return web.json_response(data=portfolio.model_dump_json())
