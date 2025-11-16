import asyncio
import logging
from typing import cast

import numpy as np
from numpy import random
from numpy.typing import NDArray
from scipy import stats  # type: ignore[reportMissingTypeStubs]

from poptimizer import consts
from poptimizer.domain.evolve import evolve
from poptimizer.domain.portfolio import forecasts, portfolio
from poptimizer.use_cases import handler


class ForecastHandler:
    def __init__(self) -> None:
        self._lgr = logging.getLogger()

    async def __call__(
        self,
        ctx: handler.Ctx,
        msg: handler.ModelDeleted | handler.ModelEvaluated,
    ) -> None:
        forecast = await ctx.get_for_update(forecasts.Forecast)
        if forecast.day < msg.day:
            forecast.init_day(msg.day)

        match msg:
            case handler.ModelDeleted():
                forecast.models -= {msg.uid}
            case handler.ModelEvaluated():
                forecast.models.add(msg.uid)

        port = await ctx.get(portfolio.Portfolio)

        if forecast.update_required(port.ver):
            await self._update(ctx, forecast, port)

        ctx.publish(handler.ForecastsAnalyzed(day=forecast.day))

    async def _update(
        self,
        ctx: handler.Ctx,
        forecast: forecasts.Forecast,
        port: portfolio.Portfolio,
    ) -> None:
        positions = port.normalized_positions
        port_tickers = tuple(pos.ticker for pos in positions)

        models: list[evolve.Model] = []

        for uid in frozenset(forecast.models):
            model = await ctx.get(evolve.Model, uid)
            if model.day != port.day or model.tickers != port_tickers or model.forecast_days != port.forecast_days:
                forecast.models.remove(uid)
                continue

            models.append(model)

        if len(models) <= 1 or not any(pos.weight for pos in positions):
            return

        forecast.day = port.day
        forecast.portfolio_ver = port.ver
        forecast.forecast_days = port.forecast_days
        forecast.illiquid = port.illiquid
        forecast.forecasts_count = len(models)

        await asyncio.to_thread(self._update_forecast, forecast, models, positions)

        self._send_new_recommendation(forecast)

    def _update_forecast(
        self,
        forecast: forecasts.Forecast,
        models: list[evolve.Model],
        positions: list[portfolio.NormalizedPosition],
    ) -> None:
        weights = np.array([pos.weight for pos in positions]).reshape(-1, 1)
        turnover = np.array([pos.norm_turnover for pos in positions]).reshape(-1, 1)

        means: list[NDArray[np.double]] = []
        port_means: list[float] = []

        stds: list[NDArray[np.double]] = []
        port_stds: list[float] = []

        betas: list[NDArray[np.double]] = []
        grads: list[NDArray[np.double]] = []
        costs: list[NDArray[np.double]] = []

        risk_tol: list[float] = []
        p_value = consts.P_VALUE * 2 / len(positions)

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

        forecast.mean = np.median(port_means).item()  # type: ignore[reportUnknownMemberType]
        forecast.std = np.median(port_stds).item()  # type: ignore[reportUnknownMemberType]
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
            rng=random.default_rng(0),
        ).confidence_interval
        _, median_grads_upper = stats.bootstrap(  # type: ignore[reportUnknownMemberType]
            stacked_grads + stacked_costs,
            _median,
            confidence_level=(1 - p_value),
            paired=True,
            rng=random.default_rng(0),
        ).confidence_interval

        median_risk_tol = np.median(risk_tol)  # type: ignore[reportUnknownMemberType]

        forecast.positions = []
        for n, pos in enumerate(positions):
            forecast.positions.append(
                forecasts.Position(
                    ticker=pos.ticker,
                    weight=pos.weight,
                    mean=median_mean[n],
                    std=median_std[n],
                    beta=median_betas[n],
                    grad=median_grads[n],
                    grad_lower=np.nan_to_num(cast("float", median_grads_lower[n]), nan=-np.inf),
                    grad_upper=np.nan_to_num(cast("float", median_grads_upper[n]), nan=np.inf),
                    accounts=pos.accounts,
                )
            )

        forecast.risk_tolerance = median_risk_tol.item()  # type: ignore[reportUnknownMemberType]

    def _send_new_recommendation(self, forecast: forecasts.Forecast) -> None:
        _, buy, sell = forecast.buy_sell()

        match not sell:
            case False:
                self._lgr.warning(
                    "New %d forecasts update - sell %s and buy %s",
                    forecast.forecasts_count,
                    sell[-1].ticker,
                    buy[0].ticker,
                )
            case True:
                self._lgr.warning(
                    "New %d forecasts update - portfolio is close to optimal, allocate free cash to %s",
                    forecast.forecasts_count,
                    buy[0].ticker,
                )


def _median(*args: tuple[NDArray[np.double], ...]) -> list[NDArray[np.double]]:
    return [cast("NDArray[np.double]", np.median(sample)) for sample in args]
