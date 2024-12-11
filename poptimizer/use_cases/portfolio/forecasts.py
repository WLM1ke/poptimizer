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
        port_means: list[float] = []

        stds: list[NDArray[np.double]] = []
        port_stds: list[float] = []

        betas: list[NDArray[np.double]] = []
        grads: list[NDArray[np.double]] = []

        for uid in forecast.models:
            model = await ctx.get(evolve.Model, uid)
            if model.day != day or model.tickers != tickers:
                forecast.models.remove(uid)
                continue

            mean: NDArray[np.double] = np.array(model.mean)
            means.append(mean)
            port_mean = weights.reshape(1, -1) @ mean
            port_means.append(port_mean.item())

            cov: NDArray[np.double] = np.array(model.cov)
            stds.append(np.diag(cov).reshape(-1, 1) ** 0.5)
            covs = cov @ weights
            port_var = weights.reshape(1, -1) @ covs
            port_std = port_var**0.5
            port_stds.append(port_std.item())
            beta = covs / port_var
            betas.append(beta)

            # U = risk_tolerance * (mp - sp ** 2 / 2) - (1 - risk_tolerance) * sp  # noqa: ERA001
            grad_log_ret = (mean - port_mean) - port_var * (beta - 1)
            grad_err = port_std * (beta - 1)
            grads.append(model.risk_tolerance * grad_log_ret - (1 - model.risk_tolerance) * grad_err)

        forecast.mean = np.median(port_means).item()
        forecast.std = np.median(port_stds).item()

        stacked_mean = np.hstack(means)
        median_mean = np.median(stacked_mean, axis=1)

        stacked_stds = np.hstack(stds)
        median_std = np.median(stacked_stds, axis=1)

        stacked_betas = np.hstack(betas)
        median_betas = np.median(stacked_betas, axis=1)

        stacked_grads = np.hstack(grads)
        median_grads = np.median(stacked_grads, axis=1)

        forecast.positions = []
        for n, ticker in enumerate(tickers):
            forecast.positions.append(
                forecasts.Position(
                    ticker=ticker,
                    mean=median_mean[n],
                    std=median_std[n],
                    beta=median_betas[n],
                    grad=median_grads[n],
                )
            )

        forecast.forecasts = len(means)
        forecast.portfolio_ver = port.ver
