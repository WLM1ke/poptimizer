from aiohttp import web

from poptimizer.controllers.bus import msg
from poptimizer.use_cases.requests import portfolio, raw


class Handlers:
    def __init__(
        self,
        app: web.Application,
        bus: msg.Bus,
    ) -> None:
        self._bus = bus

        app.add_routes([web.get("/portfolio", self.get_portfolio)])
        app.add_routes([web.post("/portfolio/{account}", self.create_acount)])
        app.add_routes([web.delete("/portfolio/{account}", self.remove_acount)])
        app.add_routes([web.post("/portfolio/{account}/{ticker}", self.update_position)])
        app.add_routes([web.put("/exclude/{ticker}", self.exclude_ticker)])
        app.add_routes([web.delete("/exclude/{ticker}", self.not_exclude_ticker)])
        app.add_routes([web.get("/forecast", self.get_forecast)])
        app.add_routes([web.get("/dividends", self.get_div_tickers)])
        app.add_routes([web.get("/dividends/{ticker}", self.get_dividends)])
        app.add_routes([web.put("/dividends/{ticker}", self.update_dividends)])

    async def get_portfolio(self, request: web.Request) -> web.StreamResponse:  # noqa: ARG002
        port = await self._bus.request(portfolio.GetPortfolio())

        return web.json_response(text=port.model_dump_json())

    async def create_acount(self, request: web.Request) -> web.StreamResponse:
        port = await self._bus.request(portfolio.CreateAccount.model_validate(request.match_info))

        return web.json_response(text=port.model_dump_json())

    async def remove_acount(self, request: web.Request) -> web.StreamResponse:
        port = await self._bus.request(portfolio.RemoveAccount.model_validate(request.match_info))

        return web.json_response(text=port.model_dump_json())

    async def update_position(self, request: web.Request) -> web.StreamResponse:
        port = await self._bus.request(portfolio.Position.model_validate(await request.json() | request.match_info))

        return web.json_response(text=port.model_dump_json())

    async def exclude_ticker(self, request: web.Request) -> web.StreamResponse:
        tickers = await self._bus.request(portfolio.ExcludeTicker.model_validate(request.match_info))

        return web.json_response(text=tickers.model_dump_json())

    async def not_exclude_ticker(self, request: web.Request) -> web.StreamResponse:
        tickers = await self._bus.request(portfolio.NotExcludeTicker.model_validate(request.match_info))

        return web.json_response(text=tickers.model_dump_json())

    async def get_forecast(self, request: web.Request) -> web.StreamResponse:  # noqa: ARG002
        forecast = await self._bus.request(portfolio.GetForecast())

        return web.json_response(text=forecast.model_dump_json())

    async def get_div_tickers(self, request: web.Request) -> web.StreamResponse:  # noqa: ARG002
        div = await self._bus.request(raw.GetDivTickers())

        return web.json_response(text=div.model_dump_json())

    async def get_dividends(self, request: web.Request) -> web.StreamResponse:
        div = await self._bus.request(raw.GetDividends.model_validate(request.match_info))

        return web.json_response(text=div.model_dump_json())

    async def update_dividends(self, request: web.Request) -> web.StreamResponse:
        div = await self._bus.request(raw.UpdateDividends.model_validate(await request.json() | request.match_info))

        return web.json_response(text=div.model_dump_json())
