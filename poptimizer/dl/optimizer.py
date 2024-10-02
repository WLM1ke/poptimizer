import numpy as np
import scipy
from numpy.typing import NDArray
from pydantic import BaseModel

from poptimizer.dl import ledoit_wolf
from poptimizer.domain import consts


class Desc(BaseModel):
    risk_tolerance: float


class OptimizationResult(BaseModel):
    ret: float
    avr: float
    ret_plan: float
    std_plan: float
    pos: int
    max_weight: float

    def __str__(self) -> str:
        delta = self.ret - self.avr

        return " / ".join(
            [
                f"DELTA = {delta:>8.2%}",
                f"RET = { self.ret:>8.2%}",
                f"AVR = {self.avr:>8.2%}",
                f"PLAN = {self.ret_plan:>7.2%}",
                f"STD = {self.std_plan:>7.2%}",
                f"POS = {self.pos:>3}",
                f"MAX = {self.max_weight:>7.2%}",
            ],
        )


def optimize(
    mean: NDArray[np.double],
    variance: NDArray[np.double],
    labels: NDArray[np.double],
    tot_ret: NDArray[np.double],
    desc: Desc,
    forecast_days: int,
) -> OptimizationResult:
    mean *= consts.YEAR_IN_TRADING_DAYS / forecast_days
    variance *= consts.YEAR_IN_TRADING_DAYS / forecast_days
    labels *= consts.YEAR_IN_TRADING_DAYS / forecast_days

    weights, sigma = _opt_weight(mean, variance, tot_ret, desc.risk_tolerance)

    return OptimizationResult(
        ret=(weights.T @ labels).item(),
        avr=labels.mean(),
        ret_plan=(weights * mean).sum(),
        std_plan=(weights.T @ sigma @ weights).item() ** 0.5,
        pos=int(1 / (weights**2).sum()),
        max_weight=weights.max(),
    )


def _opt_weight(
    mean: NDArray[np.double],
    variance: NDArray[np.double],
    tot_ret: NDArray[np.double],
    risk_tolerance: float,
) -> tuple[NDArray[np.double], NDArray[np.double]]:
    sigma = ledoit_wolf.ledoit_wolf_cor(tot_ret)[0]
    std = variance**0.5
    sigma = std.T * sigma * std

    weights = np.ones_like(mean).flatten()
    weights /= weights.sum()

    rez = scipy.optimize.minimize(
        _Utility(risk_tolerance, mean, sigma),
        weights,
        bounds=[(0, None) for _ in weights],
        constraints=[
            {
                "type": "eq",
                "fun": lambda _weights: _weights.sum() - 1,
                "jac": np.ones_like,
            },
        ],
    )

    weights = rez.x / rez.x.sum()

    return weights.reshape(-1, 1), sigma


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
