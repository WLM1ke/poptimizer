"""Метрики для одного прогноза."""
import statistics

import numpy as np
import pandas as pd

from poptimizer import Portfolio, CASH, PORTFOLIO, evolve


class MetricsSingle:
    """Реализует основные метрики портфеля для одного прогноза."""

    def __init__(self, portfolio: Portfolio, mean: pd.Series, cov: np.array):
        """Использует прогноз для построения основных метрик позиций портфеля.

        Приближенно максимизируется геометрическая доходность портфеля исходя из прогноза. Для чего
        рассчитывается ее производные по долям активов в портфеле на основе доходностей, СКО и бет.

        :param portfolio:
            Портфель, для которого рассчитываются метрики.
        :param mean:
            Прогноз доходности.
        :param cov:
            Прогноз ковариационной матрицы.
        """
        self._portfolio = portfolio
        self._mean = mean
        self._cov = cov

    @property
    def mean(self) -> pd.Series:
        """Матожидание доходности по всем позициям портфеля."""
        mean = self._mean
        mean[CASH] = 0
        weighted_mean = mean * self._portfolio.weight[mean.index]
        mean[PORTFOLIO] = weighted_mean.sum(axis=0)
        return mean

    @property
    def std(self) -> pd.Series:
        """СКО дивидендной доходности по всем позициям портфеля."""
        portfolio = self._portfolio
        cov = self._cov
        std = np.diag(cov) ** 0.5
        std = pd.Series(std, index=portfolio.index[:-2])
        std[CASH] = 0
        weight = portfolio.weight[:-2].values
        portfolio_var = weight.reshape(1, -1) @ cov @ weight.reshape(-1, 1)
        std[PORTFOLIO] = portfolio_var[0, 0] ** 0.5
        return std

    @property
    def beta(self) -> pd.Series:
        """Беты относительно доходности портфеля."""
        portfolio = self._portfolio
        cov = self._cov
        weight = portfolio.weight[:-2].values
        beta = cov @ weight.reshape(-1, 1)
        beta = beta / (weight.reshape(1, -1) * beta)
        beta = pd.Series(beta.flatten(), index=portfolio.index[:-2])
        beta[CASH] = 0
        beta[PORTFOLIO] = 1
        return beta

    @property
    def r_geom(self) -> pd.Series:
        """Приближенная оценка геометрической доходности.

        ДЛя портфеля равна арифметической доходности минус половина квадрата СКО. Для остальных
        активов рассчитывается как сумма градиента и показателя для портфеля.

        При правильной реализации взвешенная по долям отдельных позиций граница равна границе по
        портфелю в целом.
        """
        r_geom = self.mean[PORTFOLIO] - self.std[PORTFOLIO] ** 2 / 2
        return self.gradient.add(r_geom)

    @property
    def gradient(self) -> pd.Series:
        """Рассчитывает производную приближенного значения геометрической доходности по долям акций.

        В общем случае равна (m - mp) - (b - 1) * sp ** 2, m и mp - доходность актива и портфеля,
        соответственно, sp - СКО портфеля, b - бета актива.

        Долю актива с максимальным градиентом необходимо наращивать, а с минимальным сокращать. Так как
        важную роль в градиенте играет бета, то во многих случаях выгодно наращивать долю не той бумаги,
        у которой достаточно низкая бета при высокой ожидаемой доходности.

        При правильной реализации взвешенный по долям отдельных позиций градиент равен градиенту по
        портфелю в целом и равен 0.
        """
        mean = self.mean
        mean_gradient = mean - mean[PORTFOLIO]
        risk_gradient = self.beta.sub(1) * self.std[PORTFOLIO] ** 2
        return mean_gradient - risk_gradient


class MetricsResample:
    """Реализует основные метрики портфеля для набора прогнозов."""

    def __init__(self, portfolio: Portfolio):
        """Использует прогноз для построения основных метрик позиций портфеля.

        Приближенно максимизируется геометрическая доходность портфеля исходя из прогноза. Для чего
        рассчитывается ее производные по долям активов в портфеле на основе доходностей, СКО и бет.

        :param portfolio:
            Портфель, для которого рассчитываются метрики.
        """
        self._portfolio = portfolio
        tickers = tuple(portfolio.index[:-2])
        date = portfolio.date
        self._metrics = []
        for mean, cov in evolve.get_forecasts(tickers, date):
            self._metrics.append(MetricsSingle(portfolio, mean, cov))

    def __str__(self) -> str:
        frames = [
            self.mean,
            self.std,
            self.beta,
            self.r_geom,
            self.gradient,
            self.error,
        ]
        df = pd.concat(frames, axis=1)
        df.columns = ["MEAN", "STD", "BETA", "R_GEOM", "GRADIENT", "ERROR"]
        return f"\nКЛЮЧЕВЫЕ МЕТРИКИ ПОРТФЕЛЯ" f"\n" f"\n{df}"

    @property
    def mean(self) -> pd.Series:
        """Матожидание доходности по всем позициям портфеля."""
        return statistics.mean(metric.mean for metric in self._metrics)

    @property
    def std(self) -> pd.Series:
        """СКО дивидендной доходности по всем позициям портфеля."""
        return statistics.mean(metric.std for metric in self._metrics)

    @property
    def beta(self) -> pd.Series:
        """Беты относительно доходности портфеля."""
        return statistics.mean(metric.beta for metric in self._metrics)

    @property
    def r_geom(self) -> pd.Series:
        """Приближенная оценка геометрической доходности.

        ДЛя портфеля равна арифметической доходности минус половина квадрата СКО. Для остальных
        активов рассчитывается как сумма градиента и показателя для портфеля.

        При правильной реализации взвешенная по долям отдельных позиций граница равна границе по
        портфелю в целом.
        """
        return statistics.mean(metric.r_geom for metric in self._metrics)

    @property
    def gradient(self) -> pd.Series:
        """Рассчитывает производную приближенного значения геометрической доходности по долям акций.

        В общем случае равна (m - mp) - (b - 1) * sp ** 2, m и mp - доходность актива и портфеля,
        соответственно, sp - СКО портфеля, b - бета актива.

        Долю актива с максимальным градиентом необходимо наращивать, а с минимальным сокращать. Так как
        важную роль в градиенте играет бета, то во многих случаях выгодно наращивать долю не той бумаги,
        у которой достаточно низкая бета при высокой ожидаемой доходности.

        При правильной реализации взвешенный по долям отдельных позиций градиент равен градиенту по
        портфелю в целом и равен 0.
        """
        return statistics.mean(metric.gradient for metric in self._metrics)

    @property
    def error(self) -> pd.Series:
        """Ошибки в оценке градиента."""
        gradients = pd.concat([metric.gradient for metric in self._metrics], axis=1)
        std = gradients.std(axis=1, ddof=1)
        return std.div(len(self._metrics) ** 0.5)
