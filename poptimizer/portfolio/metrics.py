"""Абстрактный класс с метриками портфеля"""
from abc import ABC, abstractmethod
from dataclasses import dataclass

import numpy as np
import pandas as pd

from poptimizer.config import T_SCORE
from poptimizer.portfolio.portfolio import CASH, PORTFOLIO, Portfolio


@dataclass(frozen=True)
class Forecast:
    """Класс с прогнозом"""

    date: pd.Timestamp
    tickers: list
    mean: np.array
    cov: np.array


class AbstractMetrics(ABC):
    """Реализует основные метрики портфеля."""

    def __init__(self, portfolio: Portfolio, months: int = 12):
        """Использует прогноз для построения основных метрик позиций портфеля.

        К основным метрикам относятся: доходность, СКО и бета. На основе их рассчитывается нижняя
        граница доверительного интервала через определенное число месяцев и ее градиент относительно
        веса позиции в портфеле.

        :param portfolio:
            Портфель, для которого рассчитываются метрики.
        :param months:
            Интервал в месяцах, для которого рассчитывается градиент.
        """
        self._portfolio = portfolio
        self._forecast = self._forecast_func()
        self._months = months

    def __str__(self):
        frames = [self.mean, self.std, self.beta, self.lower_bound, self.gradient]
        df = pd.concat(frames, axis=1)
        df.columns = ["MEAN", "STD", "BETA", "LOWER_BOUND", "GRADIENT"]
        return f"\nКЛЮЧЕВЫЕ МЕТРИКИ ПОРТФЕЛЯ" f"\n" f"\n{df}"

    @abstractmethod
    def _forecast_func(self) -> Forecast:
        """Функция, возвращающая Forecast в годовом исчислении.

        Прогноз должен включать доходность, ковариационную матрицу и исходный портфель.
        """

    @property
    def mean(self):
        """Матожидание доходности по всем позициям портфеля."""
        portfolio = self._portfolio
        mean = self._forecast.mean
        mean = pd.Series(mean, index=portfolio.index[:-2])
        mean[CASH] = 0
        weighted_mean = mean * self._portfolio.weight[mean.index]
        mean[PORTFOLIO] = weighted_mean.sum(axis=0)
        return mean

    @property
    def std(self):
        """СКО дивидендной доходности по всем позициям портфеля."""
        portfolio = self._portfolio
        cov = self._forecast.cov
        std = np.diag(cov) ** 0.5
        std = pd.Series(std, index=portfolio.index[:-2])
        std[CASH] = 0
        weight = portfolio.weight[:-2].values
        portfolio_var = weight.reshape(1, -1) @ cov @ weight.reshape(-1, 1)
        std[PORTFOLIO] = portfolio_var[0, 0] ** 0.5
        return std

    @property
    def beta(self):
        """Беты относительно доходности портфеля."""
        portfolio = self._portfolio
        cov = self._forecast.cov
        weight = portfolio.weight[:-2].values
        beta = cov @ weight.reshape(-1, 1) / (self.std[PORTFOLIO] ** 2)
        beta = pd.Series(beta.flatten(), index=portfolio.index[:-2])
        beta[CASH] = 0
        beta[PORTFOLIO] = 1
        return beta

    # noinspection PyTypeChecker
    @property
    def lower_bound(self):
        """Рассчитывает вклад в нижнюю границу доверительного интервала для доходности.


        Используемая t-статистика берется из файла настроек. Метрики пересчитываются на указанное
        число месяцев - для доходности линейно, для СКО - пропорционально корню.

        При правильной реализации взвешенная по долям отдельных позиций граница равна границе по
        портфелю в целом.
        """
        years = self._months / 12
        mean = self.mean * years
        risk = self.std[PORTFOLIO] * (years ** 0.5) * self.beta
        lower_bound = mean - T_SCORE * risk
        return lower_bound

    @property
    def gradient(self):
        """Рассчитывает производную нижней границы по доле актива в портфеле.

        В общем случае равна (m - mp) - t * sp * (b - 1), m и mp - доходность актива и портфеля,
        соответственно, t - t-статистика, sp - СКО портфеля, b - бета актива.

        Долю актива с максимальным градиентом необходимо наращивать, а с минимальным сокращать. Так как
        важную роль в градиенте играет бета, то во многих случаях выгодно наращивать долю не той бумаги,
        у которой достаточно низкая бета при высокой дивидендной доходности.

        При правильной реализации взвешенный по долям отдельных позиций градиент равен градиенту по
        портфелю в целом и равен 0.
        """
        years = self._months / 12
        mean_gradient = (self.mean - self.mean[PORTFOLIO]) * years
        # noinspection PyTypeChecker
        risk_gradient = self.std[PORTFOLIO] * (years ** 0.5) * (self.beta - 1)
        return mean_gradient - T_SCORE * risk_gradient
