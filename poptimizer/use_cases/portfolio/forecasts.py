from typing import TYPE_CHECKING

import numpy as np

from poptimizer.domain import domain
from poptimizer.domain.evolve import evolve
from poptimizer.domain.portfolio import forecasts, portfolio
from poptimizer.use_cases import handler

if TYPE_CHECKING:
    from numpy.typing import NDArray


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

        await self._update_forecast(ctx, msg.day, forecast)

        return handler.ForecastsAnalyzed(day=msg.day)

    async def _update_forecast(self, ctx: handler.Ctx, day: domain.Day, forecast: forecasts.Forecast) -> None:
        if len(forecast.models) ** 0.5 - forecast.forecasts**0.5 < 1:
            return

        port = await ctx.get(portfolio.Portfolio)
        if port.day != day:
            return

        weights = np.array(port.weights()).reshape(-1, 1)
        tickers = port.tickers()

        means: list[NDArray[np.double]] = []
        port_mean: list[float] = []

        stds: list[NDArray[np.double]] = []
        port_std: list[float] = []

        for uid in forecast.models:
            model = await ctx.get(evolve.Model, uid)
            if model.day != day or model.tickers != tickers:
                forecast.models.remove(uid)
                continue

            mean: NDArray[np.double] = np.array(model.mean)
            means.append(mean)
            port_mean.append(np.sum(mean * weights).item())

            cov: NDArray[np.double] = np.array(model.cov)
            stds.append(np.diag(cov).reshape(-1, 1) ** 0.5)
            port_std.append(((weights.reshape(1, -1) @ cov @ weights) ** 0.5).item())

        forecast.mean = np.median(port_mean).item()
        forecast.std = np.median(port_std).item()

        stacked_mean = np.hstack(means)
        median_mean = np.median(stacked_mean, axis=1)

        stacked_stds = np.hstack(stds)
        median_std = np.median(stacked_stds, axis=1)

        forecast.positions = []
        for n, ticker in enumerate(tickers):
            forecast.positions.append(
                forecasts.Position(
                    ticker=ticker,
                    mean=median_mean[n],
                    std=median_std[n],
                )
            )

        forecast.forecasts = len(means)
        forecast.portfolio_ver = port.ver
