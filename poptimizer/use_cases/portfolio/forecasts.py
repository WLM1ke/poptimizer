import asyncio
from typing import cast

import numpy as np
from numpy.typing import NDArray
from scipy import stats  # type: ignore[reportMissingTypeStubs]

from poptimizer import consts
from poptimizer.domain.evolve import evolve
from poptimizer.domain.portfolio import forecasts, portfolio
from poptimizer.use_cases import handler


class ForecastHandler:
    async def __call__(
        self,
        ctx: handler.Ctx,
        msg: handler.ModelDeleted | handler.ModelEvaluated | handler.PositionsUpdated,
    ) -> handler.ForecastsAnalyzed | None:
        forecast = await ctx.get_for_update(forecasts.Forecast)
        if forecast.day < msg.day:
            forecast.init_day(msg.day)

        match msg:
            case handler.PositionsUpdated():
                port = await ctx.get(portfolio.Portfolio)
                if forecast.portfolio_ver < port.ver:
                    forecast.outdated = True

                return None
            case handler.ModelDeleted():
                forecast.models -= {msg.uid}
            case handler.ModelEvaluated():
                forecast.models.add(msg.uid)

        if forecast.update_required():
            await self._update(ctx, forecast)

        return handler.ForecastsAnalyzed(day=msg.day)

    async def _update(
        self,
        ctx: handler.Ctx,
        forecast: forecasts.Forecast,
    ) -> None:
        port = await ctx.get(portfolio.Portfolio)
        tickers = port.tickers()

        models: list[evolve.Model] = []

        for uid in frozenset(forecast.models):
            model = await ctx.get(evolve.Model, uid)
            if model.day != port.day or model.tickers != tickers or model.forecast_days != port.forecast_days:
                forecast.models.remove(uid)
                continue

            models.append(model)

        if len(models) <= 1:
            return

        await asyncio.to_thread(
            self._update_forecast,
            port,
            forecast,
            models,
        )

    def _update_forecast(
        self,
        port: portfolio.Portfolio,
        forecast: forecasts.Forecast,
        models: list[evolve.Model],
    ) -> None:
        tickers = port.tickers()
        weights = np.array(port.weights()).reshape(-1, 1)
        turnover = np.array(port.normalized_turnover()).reshape(-1, 1)

        means: list[NDArray[np.double]] = []
        port_means: list[float] = []

        stds: list[NDArray[np.double]] = []
        port_stds: list[float] = []

        betas: list[NDArray[np.double]] = []
        grads: list[NDArray[np.double]] = []
        costs: list[NDArray[np.double]] = []

        risk_tol: list[float] = []
        p_value = consts.P_VALUE * 2 / len(tickers)

        for model in models:
            mean: NDArray[np.double] = np.array(model.mean)
            means.append(mean)
            port_mean = weights.reshape(1, -1) @ mean
            port_means.append(port_mean.item())

            cov: NDArray[np.double] = np.array(model.cov)
            std = np.diag(cov).reshape(-1, 1) ** 0.5
            stds.append(std)
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
            # 2.3 https://arxiv.org/pdf/1705.00109.pdf
            # 2.2 Rule of thumb, trading one day’s volume moves the price by about one day’s volatility
            # Here grad by weight
            costs.append(
                (consts.YEAR_IN_TRADING_DAYS / model.forecast_days)
                * (
                    consts.COSTS
                    + (std / consts.YEAR_IN_TRADING_DAYS**0.5) * consts.IMPACT_COSTS_SCALE * (weights / turnover) ** 0.5
                )
            )

            risk_tol.append(model.risk_tolerance)

        forecast.mean = np.median(port_means).item()
        forecast.std = np.median(port_stds).item()
        median_mean = np.median(np.hstack(means), axis=1)
        median_std = np.median(np.hstack(stds), axis=1)
        median_betas = np.median(np.hstack(betas), axis=1)

        stacked_grads = np.hstack(grads)
        median_grads = np.median(stacked_grads, axis=1)

        stacked_costs = np.hstack(costs)
        median_grads_lower, _ = stats.bootstrap(  # type: ignore[reportUnknownMemberType]
            stacked_grads - stacked_costs,
            _median,
            confidence_level=(1 - p_value),
            paired=True,
            random_state=0,
        ).confidence_interval
        _, median_grads_upper = stats.bootstrap(  # type: ignore[reportUnknownMemberType]
            stacked_grads + stacked_costs,
            _median,
            confidence_level=(1 - p_value),
            paired=True,
            random_state=0,
        ).confidence_interval

        median_risk_tol = np.median(risk_tol)

        forecast.positions = []
        for n, ticker in enumerate(tickers):
            forecast.positions.append(
                forecasts.Position(
                    ticker=ticker,
                    weight=weights[n, 0],
                    mean=median_mean[n],
                    std=median_std[n],
                    beta=median_betas[n],
                    grad=median_grads[n],
                    grad_lower=cast(float, median_grads_lower[n]),
                    grad_upper=cast(float, median_grads_upper[n]),
                )
            )

        forecast.risk_tolerance = median_risk_tol.item()
        forecast.forecasts_count = len(means)
        forecast.portfolio_ver = port.ver
        forecast.outdated = False


def _median(*args: tuple[NDArray[np.double], ...]) -> list[NDArray[np.double]]:
    return [cast(NDArray[np.double], np.median(sample)) for sample in args]
