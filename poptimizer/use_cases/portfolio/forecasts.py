from poptimizer.domain.portfolio import forecasts
from poptimizer.use_cases import handler


class ForecastHandler:
    async def __call__(
        self, ctx: handler.Ctx, msg: handler.ModelDeleted | handler.ModelEvaluated
    ) -> handler.ForecastsAnalyzed:
        forecast = await ctx.get_for_update(forecasts.Forecast)
        forecast.init_day(msg.day)

        return handler.ForecastsAnalyzed(day=msg.day)
