from poptimizer.domain.portfolio import forecasts
from poptimizer.use_cases import handler


class ForecastHandler:
    async def __call__(self, ctx: handler.Ctx, msg: handler.ForecastCreated) -> None:
        forecast = await ctx.get_for_update(forecasts.Forecast)
        forecast.init_day(msg.day)
