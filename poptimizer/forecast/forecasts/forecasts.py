import asyncio
from datetime import UTC, datetime
from typing import Annotated, Final, cast

import numpy as np
from numpy import random
from numpy.typing import NDArray
from pydantic import (
    AfterValidator,
    AwareDatetime,
    BaseModel,
    Field,
    FiniteFloat,
    NonNegativeFloat,
    NonNegativeInt,
    PlainSerializer,
    PositiveInt,
)
from scipy import stats  # type: ignore[reportMissingTypeStubs]

from poptimizer.core import consts, domain, fsm
from poptimizer.evolve.evolution import evolve
from poptimizer.portfolio.port import portfolio

_MINIMAL_FORECASTS_AMOUNT: Final = 4


class Position(BaseModel):
    ticker: domain.Ticker
    weight: NonNegativeFloat
    norm_turnover: NonNegativeFloat
    mean: FiniteFloat
    std: NonNegativeFloat
    beta: FiniteFloat
    grad: FiniteFloat
    grad_lower: float
    grad_upper: float
    accounts: list[domain.AccName]


class Forecast(domain.EntityOld):
    day: domain.Day = consts.START_DAY
    portfolio_updated_at: Annotated[
        AwareDatetime,
        PlainSerializer(lambda dt: int(dt.timestamp()), return_type=int),
    ] = datetime.fromtimestamp(0, tz=UTC)
    forecast_days: PositiveInt = 1
    forecasts_cnt: NonNegativeInt = 0
    illiquid: Annotated[
        set[domain.Ticker],
        PlainSerializer(
            list,
            return_type=list,
        ),
    ] = Field(default_factory=set[domain.Ticker])
    positions: Annotated[
        list[Position],
        AfterValidator(domain.sorted_with_ticker_field_validator),
    ] = Field(default_factory=list[Position])
    risk_tolerance: float = Field(0, ge=0, le=1)
    mean: FiniteFloat = 0
    std: NonNegativeFloat = 0

    def init_day(self, port: portfolio.Portfolio) -> None:
        self.day = port.day
        self.forecast_days = port.forecast_days
        self.forecasts_cnt = 0
        self.illiquid = port.illiquid
        self.portfolio_updated_at = port.updated_at
        self._build_positions(port)

    def _build_positions(self, port: portfolio.Portfolio) -> None:

        self.positions = [
            Position(
                ticker=pos.ticker,
                weight=pos.weight,
                norm_turnover=pos.norm_turnover,
                mean=0,
                std=0,
                beta=0,
                grad=0,
                grad_lower=0,
                grad_upper=0,
                accounts=pos.accounts,
            )
            for pos in port.normalized_positions
        ]

    def update_positions(self, port: portfolio.Portfolio) -> None:
        self.portfolio_updated_at = port.updated_at
        self._build_positions(port)

    def buy_sell(self) -> tuple[float, list[Position], list[Position]]:
        if self.forecasts_cnt == 0:
            return 0, [], []

        buy = sorted(
            (pos for pos in self.positions if pos.ticker not in self.illiquid),
            key=lambda pos: pos.grad_lower,
            reverse=True,
        )
        best_lower_grad = buy[0].grad_lower
        buy = [pos for pos in buy if pos.grad_upper > best_lower_grad]

        sell = sorted((pos for pos in self.positions if pos.accounts), key=lambda pos: pos.grad_upper)

        for i, (b, s) in enumerate(zip(buy, sell, strict=False)):
            if b.grad_lower < s.grad_upper:
                if i == 0:
                    break

                sell = sell[i - 1 :: -1]
                buy = buy[: i + (buy[i].grad_lower > sell[0].grad_upper)]
                breakeven = (buy[-1].grad_lower + sell[0].grad_upper) / 2

                return breakeven, buy, sell

        if buy:
            return buy[0].grad_lower, buy[:1], []

        return 0, [], []


async def update(ctx: fsm.Ctx) -> None:
    forecast = await ctx.get_for_update(Forecast)
    models = await ctx.get_models(forecast.day)

    if len(models) < _MINIMAL_FORECASTS_AMOUNT:
        return

    await asyncio.to_thread(_update, forecast, models)

    _send_new_recommendation(ctx, forecast)


def _update(forecast: Forecast, models: list[evolve.Model]) -> None:
    forecast.forecasts_cnt = len(models)

    weights = np.array([pos.weight for pos in forecast.positions]).reshape(-1, 1)
    turnover = np.array([pos.norm_turnover or 1 for pos in forecast.positions]).reshape(-1, 1)

    means: list[NDArray[np.double]] = []
    port_means: list[float] = []

    stds: list[NDArray[np.double]] = []
    port_stds: list[float] = []

    betas: list[NDArray[np.double]] = []
    grads: list[NDArray[np.double]] = []
    costs: list[NDArray[np.double]] = []

    risk_tol: list[float] = []
    p_value = consts.P_VALUE * 2 / len(forecast.positions)

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
        risk_tolerance = model.genotype.risk.risk_tolerance
        grads.append(risk_tolerance * grad_log_ret - (1 - risk_tolerance) * grad_err)
        # 2.3 https://arxiv.org/pdf/1705.00109.pdf
        # 2.2 Rule of thumb, trading one day’s volume moves the price by about one day’s volatility
        # Here grad by weight
        costs.append(
            (consts.YEAR_IN_TRADING_DAYS / forecast.forecast_days)
            * (
                consts.COSTS
                + (std / consts.YEAR_IN_TRADING_DAYS**0.5) * consts.IMPACT_COSTS_SCALE * (weights / turnover) ** 0.5
            )
        )

        risk_tol.append(risk_tolerance)

    forecast.mean = np.median(port_means).item()  # type: ignore[reportUnknownMemberType]
    forecast.std = np.median(port_stds).item()  # type: ignore[reportUnknownMemberType]
    forecast.risk_tolerance = np.median(risk_tol).item()  # type: ignore[reportUnknownMemberType]

    median_mean = np.median(np.hstack(means), axis=1)
    median_std = np.median(np.hstack(stds), axis=1)
    median_betas = np.median(np.hstack(betas), axis=1)

    stacked_grads = np.hstack(grads)
    median_grads = np.median(stacked_grads, axis=1)

    stacked_costs = np.hstack(costs)
    median_grads_lower = stats.bootstrap(  # type: ignore[reportUnknownMemberType]
        stacked_grads - stacked_costs,
        _median,
        confidence_level=(1 - p_value),
        paired=True,
        rng=random.default_rng(0),
    ).confidence_interval.low
    median_grads_lower: NDArray[np.double] = np.nan_to_num(median_grads_lower, nan=-np.inf)  # type: ignore[reportUnknownMemberType]

    median_grads_upper = stats.bootstrap(  # type: ignore[reportUnknownMemberType]
        stacked_grads + stacked_costs,
        _median,
        confidence_level=(1 - p_value),
        paired=True,
        rng=random.default_rng(0),
    ).confidence_interval.high
    median_grads_upper: NDArray[np.double] = np.nan_to_num(median_grads_upper, nan=np.inf)  # type: ignore[reportUnknownMemberType]

    for n, pos in enumerate(forecast.positions):
        pos.mean = median_mean[n]
        pos.std = median_std[n]
        pos.beta = median_betas[n]
        pos.grad = median_grads[n]
        pos.grad_lower = median_grads_lower[n]
        pos.grad_upper = median_grads_upper[n]


def _send_new_recommendation(ctx: fsm.Ctx, forecast: Forecast) -> None:
    _, buy, sell = forecast.buy_sell()

    if not sell:
        ctx.warning(
            "New %d forecasts update - portfolio is close to optimal, allocate free cash to %s",
            forecast.forecasts_cnt,
            buy[0].ticker,
        )

        return

    ctx.warning(f"New {forecast.forecasts_cnt} forecasts update has trade recommendations")

    for pos in buy:
        ctx.warning(f"Buy {pos.ticker} with weight {pos.weight:.2%}")

    for pos in sell:
        accounts = ", ".join(sorted(pos.accounts))
        ctx.warning(f"Sell {pos.ticker} with weight {pos.weight:.2%} from {accounts}")


def _median(*args: tuple[NDArray[np.double], ...]) -> list[NDArray[np.double]]:
    return [cast("NDArray[np.double]", np.median(sample)) for sample in args]
