from aiohttp import web

from poptimizer.controllers import middleware
from poptimizer.portfolio import contracts


class Views:
    def __init__(self, app: web.Application, requester: middleware.Requester) -> None:
        self._requester = requester

        app.add_routes([web.get("/portfolio", self.get)])

    async def get(self, request: web.Request) -> web.StreamResponse:  # noqa: ARG002
        portfolio = await self._requester.request(contracts.GetPortfolio())

        return web.json_response(data=portfolio.model_dump_json())
