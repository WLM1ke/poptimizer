"""Метрики для одного прогноза и набора прогнозов."""
import functools

import numpy as np
import pandas as pd

from poptimizer import config, evolve
from poptimizer.data.views import indexes
from poptimizer.dl import Forecast
from poptimizer.portfolio.portfolio import CASH, PORTFOLIO, Portfolio


class MetricsSingle:  # noqa: WPS214
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
        frames = [self.mean, self.std, self.beta, self.r_adj, self.gradient]
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
    def risk_aversion(self) -> float:
        """Не любовь к риску."""
        return self._forecast.risk_aversion

    @functools.cached_property
    def error_tolerance(self) -> float:
        """Не любовь к ошибкам."""
        return self._forecast.error_tolerance

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
        portfolio_var = weight.reshape(1, -1) @ cov @ weight.reshape(-1, 1)  # noqa: WPS221
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
        beta = pd.Series(
            beta.ravel(),
            index=portfolio.index[:-2],
        )
        beta[CASH] = 0
        beta[PORTFOLIO] = 1
        beta.name = "BETA"

        return beta

    @functools.cached_property
    def r_adj(self) -> pd.Series:
        """Скорректированная с учетом риска доходность.

        Для портфеля рассчитывается по следующей формуле:

        r_adj = r - risk_aversion / 2 * s ** 2 - error_tolerance * s

        Для портфеля равна арифметической доходности минус половина квадрата СКО. Для остальных
        активов рассчитывается, как сумма градиента и показателя для портфеля.

        При правильной реализации взвешенная по долям отдельных позиций геометрическая доходность
        равна значению по портфелю в целом.
        """
        r_adj_portfolio = (
            self.mean[PORTFOLIO]
            - self.risk_aversion / 2 * self.std[PORTFOLIO] ** 2
            - self.error_tolerance * self.std[PORTFOLIO]
        )
        r_adj = r_adj_portfolio + self.gradient
        r_adj.name = "R_ADJ"

        return r_adj

    @functools.cached_property
    def gradient(self) -> pd.Series:
        """Рассчитывает производную скорректированной с учетом риска доходности.

         r_adj = r - risk_aversion / 2 * s ** 2 - error_tolerance * s, где

        risk_aversion - классическая нелюбовь к риску в задачах mean-variance оптимизации. При значении 1 в первом
        приближении максимизируется логарифм доходности или ожидаемые темпы роста портфеля.

        error_tolerance - величина минимальной требуемой величины коэффициента Шарпа или мера возможной достоверности
        оценок доходности. В рамках второй интерпретации происходит максимизация нижней границы доверительного
        интервала.

        Соответственно градиент может быть рассчитан по следующей формуле:

        gradient = (m - mp) - risk_aversion * sp ** 2 * (b - 1) - error_tolerance * sp * (b - 1), где

        m и mp - доходность актива и портфеля, соответственно,
        sp - СКО портфеля,
        b - бета актива.

        Долю актива с максимальным градиентом необходимо наращивать, а с минимальным сокращать. Так как
        важную роль в градиенте играет бета, то во многих случаях выгодно наращивать долю той бумаги,
        у которой достаточно низкая бета при высокой ожидаемой доходности.

        При правильной реализации взвешенный по долям отдельных позиций градиент равен градиенту по
        портфелю в целом и равен 0.
        """
        mean = self.mean
        mean_gradient = mean - mean[PORTFOLIO]

        risk_aversion_gradient = self.risk_aversion * self.std[PORTFOLIO] ** 2
        risk_aversion_gradient = risk_aversion_gradient * self.beta.sub(1)

        error_tolerance_gradient = self.error_tolerance * self.std[PORTFOLIO]
        error_tolerance_gradient = error_tolerance_gradient * self.beta.sub(1)

        gradient = mean_gradient - risk_aversion_gradient - error_tolerance_gradient
        gradient.name = "GRAD"

        return gradient


class MetricsResample:  # noqa: WPS214
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
            self._risk_aversion_block(),
            self._error_tolerance(),
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
    def r_adj(self) -> pd.Series:
        """Медиана для всех прогнозов приближенные оценки скорректированной доходности."""
        all_r_geom = [metric.r_adj for metric in self._metrics]
        r_geom = pd.concat(all_r_geom, axis=1).median(axis=1)
        r_geom.name = "R_ADJ"

        return r_geom

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
        quantile = " <-> ".join(quantile)

        return f"History days - ({quantile})"

    def _cor_block(self) -> str:
        """Разброс средней корреляции."""
        quantile = [0, 0.5, 1]
        quantile = np.quantile([met.cor for met in self._metrics], quantile)
        quantile = list(map(lambda num: f"{num:.2%}", quantile))
        quantile = " <-> ".join(quantile)

        return f"Correlation - ({quantile})"

    def _shrinkage_block(self) -> str:
        """Разброс среднего сжатия."""
        quantile = [0, 0.5, 1]
        quantile = np.quantile([met.shrinkage for met in self._metrics], quantile)
        quantile = list(map(lambda num: f"{num:.2%}", quantile))
        quantile = " <-> ".join(quantile)

        return f"Shrinkage - ({quantile})"

    def _risk_aversion_block(self) -> str:
        """Разброс нелюбви к риску."""
        quantile = [0, 0.5, 1]
        quantile = np.quantile([met.risk_aversion for met in self._metrics], quantile)
        quantile = list(map(lambda num: f"{num:.2f}", quantile))
        quantile = " <-> ".join(quantile)

        return f"Risk aversion - ({quantile})"

    def _error_tolerance(self) -> str:
        """Разброс нелюбви к ошибке."""
        quantile = [0, 0.5, 1]
        quantile = np.quantile([met.error_tolerance for met in self._metrics], quantile)
        quantile = list(map(lambda num: f"{num:.2f}", quantile))
        quantile = " <-> ".join(quantile)

        return f"Error tolerance - ({quantile})"

    def _main_block(self) -> str:
        """Основная информация о метриках."""
        frames = [
            self.mean,
            self.std,
            self.beta,
            self.r_adj,
            self.gradient,
        ]
        df = pd.concat(frames, axis=1)

        return f"\n{df}"

    def _grad_summary(self) -> str:
        return_ = pd.concat([metric.mean for metric in self._metrics], axis=1)
        return_ = return_.loc[PORTFOLIO].quantile(config.P_VALUE)

        risk = pd.concat([metric.std for metric in self._metrics], axis=1)
        risk = risk.loc[PORTFOLIO].quantile(1 - config.P_VALUE)

        r_adj = pd.concat([metric.r_adj for metric in self._metrics], axis=1)
        r_adj = r_adj.loc[PORTFOLIO].quantile(config.P_VALUE)

        dd = self.std[PORTFOLIO] ** 2 / self.mean[PORTFOLIO]

        strings = [
            "",
            _text_with_data("Консервативная доходность: ", return_),
            _text_with_data("Консервативный риск:       ", risk),
            _text_with_data("Консервативная метрика:    ", r_adj),
            _text_with_data("Оценка просадки:           ", dd),
        ]

        return "\n".join(strings)


def _text_with_data(text: str, num: float) -> str:
    return f"{text}{num: .2%}"
