from poptimizer.domain.portfolio import forecasts
from poptimizer.use_cases import handler


class ForecastHandler:
    async def __call__(self, ctx: handler.Ctx, msg: handler.ForecastCreated) -> None:
        port_forecast = await ctx.get_for_update(forecasts.PortForecast)

        if msg.day != port_forecast.day:
            forecast = await ctx.get(forecasts.Forecast, msg.uid)
            port_forecast.init_day(msg.day, forecast.tickers, forecast.uid)

            return

        if not port_forecast.is_new_uid(msg.uid):
            return

        for uid in port_forecast.forecasts:
            if uid != "":
                pass
