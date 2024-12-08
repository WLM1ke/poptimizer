from poptimizer.domain.portfolio import forecasts
from poptimizer.use_cases import handler


class ForecastHandler:
    async def __call__(
        self,
        ctx: handler.Ctx,
        msg: handler.ModelDeleted | handler.ModelEvaluated,
    ) -> handler.ForecastsAnalyzed:
        forecast = await ctx.get_for_update(forecasts.Forecast)
        match msg:
            case handler.ModelDeleted():
                forecast.models -= {msg.uid}
            case handler.ModelEvaluated():
                if forecast.day != msg.day:
                    forecast.init_day(msg.day)

                forecast.models.add(msg.uid)

        # if len(forecast.models) ** 0.5 - forecast.forecasts**0.5 >= 1:
        #     await self._update_forecast(ctx, forecast)

        return handler.ForecastsAnalyzed(day=msg.day)

    # async def _update_forecast(self, ctx: handler.Ctx, forecast: forecasts.Forecast) -> None:
    #     async with asyncio.TaskGroup() as tg:
    #         model_tasks = [tg.create_task(ctx.get(evolve.Model, uid)) for uid in forecast.models]
    #         port = await tg.create_task(ctx.get(portfolio.Portfolio))

    #     tickers = tuple(sorted(port.securities))
