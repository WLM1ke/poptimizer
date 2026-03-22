from poptimizer.core import fsm
from poptimizer.forecast.forecasts import forecasts
from poptimizer.portfolio.events import PositionChecked
from poptimizer.portfolio.port import portfolio


class InitForecastAction:
    async def __call__(self, ctx: fsm.Ctx) -> None:
        forecast = await ctx.get_for_update(forecasts.Forecast)
        port = await ctx.get(portfolio.Portfolio)

        if forecast.day != port.day:
            forecast.init_day(port)


class UpdateForecastAction:
    async def __call__(self, ctx: fsm.Ctx, event: PositionChecked) -> None:
        forecast = await ctx.get_for_update(forecasts.Forecast)
        if event.updated_at != forecast.portfolio_updated_at:
            port = await ctx.get(portfolio.Portfolio)
            forecast.update_positions(port)

        await forecasts.update(ctx)
