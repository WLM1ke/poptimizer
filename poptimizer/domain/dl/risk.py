import numpy as np
import scipy  # type: ignore[reportMissingTypeStubs]
from numpy.typing import NDArray
from pydantic import BaseModel, FiniteFloat, ValidationError

from poptimizer import consts, errors
from poptimizer.domain.dl import ledoit_wolf


class Cfg(BaseModel):
    risk_tolerance: float


class OptimizationResult(BaseModel):
    ret: FiniteFloat
    avr: FiniteFloat
    e_ret: FiniteFloat
    e_std: FiniteFloat
    pos: int
    weight_max: FiniteFloat

    def __str__(self) -> str:
        alfa = self.ret - self.avr

        return " / ".join(
            [
                f"Alfa = {alfa:>8.2%}",
                f"Ret = { self.ret:>8.2%}",
                f"Avr = {self.avr:>8.2%}",
                f"ERet = {self.e_ret:>7.2%}",
                f"EStd = {self.e_std:>7.2%}",
                f"Pos = {self.pos:>3}",
                f"WMax = {self.weight_max:>7.2%}",
            ],
        )


def optimize(  # noqa: PLR0913
    mean: NDArray[np.double],
    std: NDArray[np.double],
    labels: NDArray[np.double],
    tot_ret: NDArray[np.double],
    cfg: Cfg,
    forecast_days: int,
) -> OptimizationResult:
    year_multiplier = consts.YEAR_IN_TRADING_DAYS / forecast_days

    mean *= year_multiplier
    std *= year_multiplier**0.5

    weights, sigma = _opt_weight(mean, std, tot_ret, cfg)
    port_variance: float = (weights.T @ sigma @ weights).item()

    try:
        return OptimizationResult(
            ret=np.log1p((weights.T @ labels).item()) * year_multiplier,
            avr=np.log1p(labels.mean()) * year_multiplier,
            e_ret=(weights * mean).sum(),
            e_std=port_variance**0.5,
            pos=int(1 / (weights**2).sum()),
            weight_max=weights.max(),
        )
    except ValidationError as err:
        raise errors.DomainError("invalid optimization result") from err


def _opt_weight(
    mean: NDArray[np.double],
    std: NDArray[np.double],
    tot_ret: NDArray[np.double],
    cfg: Cfg,
) -> tuple[NDArray[np.double], NDArray[np.double]]:
    sigma = std.T * ledoit_wolf.ledoit_wolf_cor(tot_ret)[0] * std

    weights = np.ones_like(mean).flatten()
    weights /= weights.sum()

    rez = scipy.optimize.minimize(
        _Utility(cfg.risk_tolerance, mean, sigma),
        weights,
        bounds=[(0, None) for _ in weights],
        constraints=[
            {
                "type": "eq",
                "fun": _weight_constraint,
                "jac": np.ones_like,
            },
        ],
    )

    weights = rez.x / rez.x.sum()

    return weights.reshape(-1, 1), sigma


def _weight_constraint(weights: NDArray[np.double]) -> float:
    return weights.sum() - 1


class _Utility:
    def __init__(
        self,
        risk_tolerance: float,
        mean: NDArray[np.double],
        sigma: NDArray[np.double],
    ) -> None:
        self._risk_tolerance = risk_tolerance
        self._mean = mean
        self._sigma = sigma

    def __call__(self, weights: NDArray[np.double]) -> float:
        weights = weights.reshape(-1, 1) / weights.sum()

        variance = weights.T @ self._sigma @ weights
        log_growth = (weights.T @ self._mean) - variance / np.double(2)
        std = variance**0.5
        lower_bound = log_growth * self._risk_tolerance - (1 - self._risk_tolerance) * std

        return -float(lower_bound.item())
