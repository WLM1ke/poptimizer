from aiohttp import web

from poptimizer.service import uow
from poptimizer.core import domain
from poptimizer.data import portfolio, services


class Handlers:
    def __init__(
        self,
        app: web.Application,
        ctx_factory: uow.CtxFactory,
        port_srv: services.Portfolio,
        div_srv: services.Dividends,
    ) -> None:
        self._ctx_factory = ctx_factory
        self._port_srv = port_srv
        self._div_srv = div_srv

        app.add_routes([web.get("/portfolio", self.get_portfolio)])
        app.add_routes([web.post("/portfolio/{account}", self.create_acount)])
        app.add_routes([web.delete("/portfolio/{account}", self.remove_acount)])
        app.add_routes([web.post("/portfolio/{account}/{ticker}", self.update_position)])
        app.add_routes([web.get("/dividends", self.get_div_tickers)])
        app.add_routes([web.get("/dividends/{ticker}", self.get_dividends)])
        app.add_routes([web.put("/dividends/{ticker}", self.update_dividends)])

    async def get_portfolio(self, request: web.Request) -> web.StreamResponse:  # noqa: ARG002
        async with self._ctx_factory() as ctx:
            portfolio = await self._port_srv.get_portfolio(ctx)

            return web.json_response(text=portfolio.model_dump_json())

    async def create_acount(self, request: web.Request) -> web.StreamResponse:
        async with self._ctx_factory() as ctx:
            account = request.match_info["account"]
            port = await self._port_srv.create_account(ctx, portfolio.AccName(account))

            return web.json_response(text=port.model_dump_json())

    async def remove_acount(self, request: web.Request) -> web.StreamResponse:
        async with self._ctx_factory() as ctx:
            account = request.match_info["account"]
            port = await self._port_srv.remove_acount(ctx, portfolio.AccName(account))

            return web.json_response(text=port.model_dump_json())

    async def update_position(self, request: web.Request) -> web.StreamResponse:
        async with self._ctx_factory() as ctx:
            account = request.match_info["account"]
            ticker = request.match_info["ticker"]
            json = await request.json()
            port = await self._port_srv.update_position(
                ctx,
                name=portfolio.AccName(account),
                ticker=domain.Ticker(ticker),
                amount=json.get("amount"),
            )

            return web.json_response(text=port.model_dump_json())

    async def get_div_tickers(self, request: web.Request) -> web.StreamResponse:  # noqa: ARG002
        async with self._ctx_factory() as ctx:
            div = await self._div_srv.get_div_tickers(ctx)

            return web.json_response(text=div.model_dump_json())

    async def get_dividends(self, request: web.Request) -> web.StreamResponse:
        async with self._ctx_factory() as ctx:
            ticker = request.match_info["ticker"]
            div = await self._div_srv.get_dividends(ctx, domain.Ticker(ticker))

            return web.json_response(text=div.model_dump_json())

    async def update_dividends(self, request: web.Request) -> web.StreamResponse:
        async with self._ctx_factory() as ctx:
            json = await request.json()
            await self._div_srv.update_dividends(
                ctx,
                services.UpdateDividends.model_validate(
                    {
                        "ticker": request.match_info["ticker"],
                        "dividends": json.get("dividends"),
                    }
                ),
            )

        raise web.HTTPNoContent
