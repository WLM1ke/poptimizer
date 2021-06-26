"""Оптимизатор портфеля."""
import functools
import itertools

import pandas as pd
from scipy import stats

from poptimizer import config
from poptimizer.portfolio import metrics
from poptimizer.portfolio.portfolio import CASH, PORTFOLIO, Portfolio


class Optimizer:
    """Предлагает сделки для улучшения метрики портфеля."""

    def __init__(self, portfolio: Portfolio, p_value: float = config.P_VALUE):
        """Учитывается градиент, его ошибку и ликвидность бумаг.

        :param portfolio:
            Оптимизируемый портфель.
        :param p_value:
            Требуемая значимость отклонения градиента от нуля.
        """
        self._portfolio = portfolio
        self._p_value = p_value
        self._metrics = metrics.MetricsResample(portfolio)

    def __str__(self) -> str:
        df = self.best_combination()
        blocks = [
            "\nОПТИМИЗАЦИЯ ПОРТФЕЛЯ",
            f"forecasts = {self.metrics.count}",
            f"p-value = {self._p_value:.2%}",
            f"trials = {self.trials}",
            f"match = {len(df)}",
            f"for sale = {len(df['SELL'].unique())}",
            f"\n{df}",
        ]
        return "\n".join(blocks)

    @property
    def portfolio(self) -> Portfolio:
        """Оптимизируемый портфель."""
        return self._portfolio

    @property
    def metrics(self) -> metrics.MetricsResample:
        """Метрики портфеля."""
        return self._metrics

    @functools.cached_property
    def trials(self) -> int:
        """Количество тестов на значимость."""
        return sum(1 for _ in self._acceptable_trades())

    def best_combination(self) -> pd.DataFrame:
        """Лучшие комбинации для торговли.

        Для каждого актива, который можно продать со значимым улучшением выбирается актив с
        максимальной вероятностью улучшения.
        """
        rez = pd.DataFrame(
            list(self._wilcoxon_tests()),
            columns=[
                "SELL",
                "BUY",
                "SML_DIFF",
                "B_DIFF",
                "R_DIFF",
                "TURNOVER",
                "P_VALUE",
            ],
        )
        rez = rez.sort_values(["SML_DIFF"], ascending=[False])
        rez.index = pd.RangeIndex(start=1, stop=len(rez) + 1)

        return rez

    def _acceptable_trades(self) -> tuple[str, str, float]:
        positions = self.portfolio.index[:-2]
        weight = self.portfolio.weight
        turnover = self.portfolio.turnover_factor

        for sell, buy in itertools.product(positions, positions):
            if sell == buy:
                continue

            if weight[sell] == 0:
                continue

            factor = turnover[buy] - (weight[sell] + weight[CASH])
            if factor < 0:
                continue

            yield sell, buy, factor

    def _wilcoxon_tests(self) -> tuple[str, str, float, float, float, float]:
        """Осуществляет тестирование всех допустимых пар активов с помощью теста Вилкоксона."""
        all_gradients = self.metrics.all_gradients
        means = self.metrics.mean
        betas = self.metrics.beta

        for sell, buy, factor in self._acceptable_trades():
            mean = means[buy] - means[sell] - config.COSTS
            if _bad_mean(mean, means[PORTFOLIO]):
                continue

            diff = all_gradients.loc[buy] - all_gradients.loc[sell] - config.COSTS
            _, alfa = stats.wilcoxon(diff, alternative="greater", correction=True)
            alfa *= self.trials

            if alfa < self._p_value:
                yield [
                    sell,
                    buy,
                    diff.median(),
                    betas[sell] - betas[buy],
                    mean,
                    factor,
                    alfa,
                ]


def _bad_mean(mean: float, port_mean: float) -> bool:
    if config.MIN_RETURN is None:
        return False

    if port_mean > config.MIN_RETURN:
        return False

    return mean < 0
