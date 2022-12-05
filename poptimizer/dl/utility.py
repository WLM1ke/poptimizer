import numpy as np
import numpy.typing as npt
import scipy
from pydantic import BaseModel

from poptimizer.core import consts
from poptimizer.dl import ledoit_wolf


class Desc(BaseModel):
    """Описание параметров кривой полезности."""

    risk_tolerance: float


class Result(BaseModel):
    ret: float
    avr: float
    ret_plan: float
    std_plan: float
    pos: int
    max_weight: float

    def __str__(self) -> str:
        """Доходность портфеля с максимальными ожидаемыми темпами роста.

        Рассчитывается доходность оптимального по темпам роста портфеля в годовом выражении (RET) и
        выводится дополнительная статистика:


        - DELTA - разность доходности портфеля и бенчмарка
        - RET - доходность портфеля
        - AVR - доходность равновзвешенного портфеля в качестве простого бенчмарка
        - PLAN - ожидавшаяся доходность
        - STD - ожидавшееся СКО
        - POS - эффективное количество позиций в портфеле
        - MAX - максимальный вес актива
        """
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
    mean: npt.NDArray[np.double],
    var: npt.NDArray[np.double],
    labels: npt.NDArray[np.double],
    tot_ret: npt.NDArray[np.double],
    desc: Desc,
    forecast_days: int,
) -> Result:
    """Оптимизирует портфель и возвращает результаты сравнения с бенчмарком."""
    mean *= consts.YEAR_IN_TRADING_DAYS / forecast_days
    var *= consts.YEAR_IN_TRADING_DAYS / forecast_days
    labels *= consts.YEAR_IN_TRADING_DAYS / forecast_days

    w, sigma = _opt_weight(mean, var, tot_ret, desc.risk_tolerance)
    ret = (w.T @ labels).item()
    avr = labels.mean()
    ret_plan = (w * mean).sum()
    std_plan = (w.reshape(1, -1) @ sigma @ w.reshape(-1, 1)).item() ** 0.5

    return Result(
        ret=ret,
        avr=avr,
        ret_plan=ret_plan,
        std_plan=std_plan,
        pos=int(1 / (w**2).sum()),
        max_weight=w.max(),
    )


def _opt_weight(
    mean: npt.NDArray[np.double],
    variance: npt.NDArray[np.double],
    tot_ret: npt.NDArray[np.double],
    risk_tolerance: float,
) -> tuple[npt.NDArray[np.double], npt.NDArray[np.double]]:
    """Веса портфеля с максимальными темпами роста и использовавшаяся ковариационная матрица.

    Задача максимизации темпов роста портфеля сводится к максимизации математического ожидания
    логарифма доходности. Дополнительно накладывается ограничение на полною отсутствие кэша и
    неотрицательные веса отдельных активов.
    """
    sigma = ledoit_wolf.ledoit_wolf_cor(tot_ret)[0]
    std = variance**0.5
    sigma = std.reshape(1, -1) * sigma * std.reshape(-1, 1)

    w = np.ones_like(mean).flatten()
    w /= w.sum()

    util = _Utility(risk_tolerance, mean, sigma)

    rez = scipy.optimize.minimize(
        lambda x: util(x),
        w,
        bounds=[(0, None) for _ in w],
        constraints=[
            {
                "type": "eq",
                "fun": lambda x: x.sum() - 1,
                "jac": lambda x: np.ones_like(x),
            },
        ],
    )

    return (rez.x / rez.x.sum()).reshape(-1, 1), sigma


class _Utility:
    def __init__(
        self,
        risk_tolerance: float,
        mean: npt.NDArray[np.double],
        sigma: npt.NDArray[np.double],
    ) -> None:
        self._risk_tolerance = risk_tolerance
        self._mean = mean
        self._sigma = sigma

    def __call__(self, w: npt.NDArray[np.float64]) -> float:
        w = w.reshape(-1, 1) / w.sum()

        variance = w.T @ self._sigma @ w
        ret = (w.T @ self._mean) - variance / np.double(2)

        return -float((ret * self._risk_tolerance - (1 - self._risk_tolerance) * variance**0.5).item())
