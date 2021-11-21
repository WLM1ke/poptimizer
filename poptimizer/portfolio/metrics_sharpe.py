"""Метрики для одного прогноза и набора прогнозов."""
import functools
from typing import Final

import numpy as np
import pandas as pd

from poptimizer import evolve
from poptimizer.data.views import indexes
from poptimizer.dl import Forecast
from poptimizer.portfolio.portfolio import CASH, PORTFOLIO, Portfolio

_P_VALUE: Final = 0.05


class MetricsSingle:
    """Реализует основные метрики портфеля для одного прогноза."""

    def __init__(self, portfolio: Portfolio, forecast: Forecast) -> None:
        """Использует прогноз для построения основных метрик позиций портфеля.

        Максимизирует отношение доходности к СКО портфеля.

        :param portfolio:
            Портфель, для которого рассчитываются метрики.
        :param forecast:
            Прогноз доходности и ковариации.
        """
        self._portfolio = portfolio
        self._forecast = forecast
        self._rf = indexes.rf(portfolio.date)

    def __str__(self) -> str:
        """Текстовое представление метрик портфеля."""
        frames = [self.mean, self.std, self.beta, self.sharpe, self.gradient]
        df = pd.concat(frames, axis=1)

        return f"\nКЛЮЧЕВЫЕ МЕТРИКИ ПОРТФЕЛЯ\n\n{df}"

    @functools.cached_property
    def history_days(self) -> int:
        """Количество дней истории для прогнозирования."""
        return self._forecast.history_days

    @functools.cached_property
    def cor(self) -> float:
        """Средняя корреляция активов."""
        return self._forecast.cor

    @functools.cached_property
    def shrinkage(self) -> float:
        """Среднее сжатие корреляционной матрицы."""
        return self._forecast.shrinkage

    @functools.cached_property
    def rf(self) -> float:
        """Безрисковая ставка."""
        return self._rf

    @functools.cached_property
    def mean(self) -> pd.Series:
        """Математическое ожидание доходности по всем позициям портфеля."""
        portfolio = self._portfolio
        mean = self._forecast.mean[portfolio.index[:-2]]
        mean[CASH] = 0
        weighted_mean = mean * portfolio.weight[mean.index]
        mean[PORTFOLIO] = weighted_mean.sum()
        mean.name = "MEAN"

        return mean

    @functools.cached_property
    def std(self) -> pd.Series:
        """СКО доходности по всем позициям портфеля."""
        portfolio = self._portfolio
        cov = self._forecast.cov
        std = np.diag(cov) ** 0.5
        std = pd.Series(std, index=portfolio.index[:-2])
        std[CASH] = 0
        weight = portfolio.weight[:-2].values
        portfolio_var = weight.reshape(1, -1) @ cov @ weight.reshape(-1, 1)
        std[PORTFOLIO] = portfolio_var.squeeze() ** 0.5
        std.name = "STD"

        return std

    @functools.cached_property
    def beta(self) -> pd.Series:
        """Беты относительно доходности портфеля."""
        portfolio = self._portfolio
        cov = self._forecast.cov
        weight = portfolio.weight[:-2].values
        beta = cov @ weight.reshape(-1, 1)
        beta = beta / (weight.reshape(1, -1) @ beta)
        beta = pd.Series(beta.ravel(), index=portfolio.index[:-2])
        beta[CASH] = 0
        beta[PORTFOLIO] = 1
        beta.name = "BETA"

        return beta

    @functools.cached_property
    def sharpe(self) -> pd.Series:
        """Отношение доходности и риска портфеля."""
        rf = self._rf
        sharpe = ((self.mean - rf) - (self.mean[PORTFOLIO] - rf) * (self.beta - 1)) / self.std[PORTFOLIO]
        sharpe.name = "SHARPE"

        return sharpe

    @functools.cached_property
    def gradient(self) -> pd.Series:
        """Производная отношения доходности и риска портфеля по долям позиций.

        Долю актива с максимальным градиентом необходимо наращивать, а с минимальным сокращать. Так как
        важную роль в градиенте играет бета, то во многих случаях выгодно наращивать долю той бумаги,
        у которой достаточно низкая бета при высокой ожидаемой доходности.

        При правильной реализации взвешенный по долям отдельных позиций градиент равен градиенту по
        портфелю в целом и равен 0.

        В общем случае градиент равен (m -(rf + b * (mp - rf))) / sp, где:

        - m и mp - доходность актива и портфеля, соответственно,
        - rf - безрисковая ставка,
        - sp - СКО портфеля,
        - b - бета актива.

        Знаменатель не влияет на знак — направление изменения доли актива для увеличения отношения
        доходность/риск. Числитель формулы имеет размерность доходности и может быть интерпретирован,
        как превышение доходности актива над SML. Таким образом, использование только числителя
        позволяет легче учесть издержки для множества прогнозов и не влияет на корректность выводов о
        требуемом направлении изменения доли актива в портфеле.

        В данной реализации используется только числитель градиента.
        """
        mean = self.mean
        rf = self._rf
        gradient = mean - (rf + (mean[PORTFOLIO] - rf) * self.beta)
        gradient.name = "GRAD"

        return gradient


class MetricsResample:
    """Реализует усредненные метрики портфеля для набора прогнозов."""

    def __init__(self, portfolio: Portfolio) -> None:
        """Использует набор прогнозов для построения основных метрик позиций портфеля.

        :param portfolio:
            Портфель, для которого рассчитываются метрики.
        """
        self._portfolio = portfolio
        tickers = tuple(portfolio.index[:-2])
        date = portfolio.date
        self._metrics = []
        for forecast in evolve.get_forecasts(tickers, date):
            self._metrics.append(MetricsSingle(portfolio, forecast))

    def __str__(self) -> str:
        """Текстовое представление информации о метриках портфеля."""
        blocks = [
            "\nКЛЮЧЕВЫЕ МЕТРИКИ ПОРТФЕЛЯ\n",
            self._history_block(),
            self._cor_block(),
            self._shrinkage_block(),
            self._main_block(),
            self._grad_summary(),
        ]

        return "\n".join(blocks)

    @functools.cached_property
    def count(self) -> int:
        """Количество прогнозов."""
        return len(self._metrics)

    @functools.cached_property
    def mean(self) -> pd.Series:
        """Медиану для всех прогнозов матожидание доходности по позициям портфеля."""
        mean = pd.concat([metric.mean for metric in self._metrics], axis=1)
        mean = mean.median(axis=1)
        mean.name = "MEAN"

        return mean

    @functools.cached_property
    def std(self) -> pd.Series:
        """Медиану для всех прогнозов СКО доходности по позициям портфеля."""
        std = pd.concat([metric.std for metric in self._metrics], axis=1)
        std = std.median(axis=1)
        std.name = "STD"

        return std

    @functools.cached_property
    def beta(self) -> pd.Series:
        """Медиана для всех прогнозов беты относительно доходности портфеля."""
        beta = pd.concat([metric.beta for metric in self._metrics], axis=1)
        beta = beta.median(axis=1)
        beta.name = "BETA"

        return beta

    @functools.cached_property
    def shape(self) -> pd.Series:
        """Медиана для всех прогнозов отношения доходности и риска."""
        sharpe = pd.concat([metric.sharpe for metric in self._metrics], axis=1)
        sharpe = sharpe.median(axis=1)
        sharpe.name = "SHARPE"

        return sharpe

    @functools.cached_property
    def all_gradients(self) -> pd.DataFrame:
        """Градиенты всех прогнозов."""
        return pd.concat([metric.gradient for metric in self._metrics], axis=1)

    @functools.cached_property
    def gradient(self) -> pd.Series:
        """Медиана для всех прогнозов производных отношения доходности и риска."""
        gradient = self.all_gradients.median(axis=1)
        gradient.name = "GRAD"

        return gradient

    def _history_block(self) -> str:
        """Разброс дней истории."""
        quantile = [0, 0.5, 1]
        quantile = np.quantile([met.history_days for met in self._metrics], quantile)
        quantile = list(map(lambda num: f"{num:.0f}", quantile))

        return f"Дней в истории - ({' <-> '.join(quantile)})"

    def _cor_block(self) -> str:
        """Разброс средней корреляции."""
        quantile = [0, 0.5, 1]
        quantile = np.quantile([met.cor for met in self._metrics], quantile)
        quantile = list(map(lambda num: f"{num:.2%}", quantile))

        return f"Корреляция - ({' <-> '.join(quantile)})"

    def _shrinkage_block(self) -> str:
        """Разброс среднего сжатия."""
        quantile = [0, 0.5, 1]
        quantile = np.quantile([met.shrinkage for met in self._metrics], quantile)
        quantile = list(map(lambda num: f"{num:.2%}", quantile))

        return f"Сжатие - ({' <-> '.join(quantile)})"

    def _main_block(self) -> str:
        """Основная информация о метриках."""
        frames = [
            self.mean,
            self.std,
            self.beta,
            self.shape,
            self.gradient,
        ]

        return f"\n{pd.concat(frames, axis=1)}"

    def _grad_summary(self) -> str:
        return_ = pd.concat([metric.mean for metric in self._metrics], axis=1)
        return_ = return_.loc[PORTFOLIO].quantile(_P_VALUE)

        risk = pd.concat([metric.std for metric in self._metrics], axis=1)
        risk = risk.loc[PORTFOLIO].quantile(1 - _P_VALUE)

        sharpe = pd.concat([metric.sharpe for metric in self._metrics], axis=1)
        sharpe = sharpe.loc[PORTFOLIO].quantile(_P_VALUE)

        strings = [
            "",
            f"Безрисковая ставка:        {self._metrics[0].rf: .4f}",
            f"Консервативная доходность: {return_: .4f}",
            f"Консервативный риск:       {risk: .4f}",
            f"Консервативный Шарп:       {sharpe: .4f}",
        ]

        return "\n".join(strings)
