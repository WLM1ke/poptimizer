"""Оптимизатор портфеля."""
import itertools
import math
from typing import Tuple

import pandas as pd
from scipy import stats

from poptimizer import config
from poptimizer.config import MAX_TRADE
from poptimizer.dl.features.data_params import FORECAST_DAYS
from poptimizer.portfolio import metrics
from poptimizer.portfolio.portfolio import Portfolio, CASH, PORTFOLIO

# Значимость отклонения градиента от нуля
P_VALUE = 0.05

# Издержки в годовом выражении для двух операций
COSTS = (config.YEAR_IN_TRADING_DAYS * 2 / FORECAST_DAYS) * (0.025 / 100)


class Optimizer:
    """Предлагает сделки для улучшения метрики портфеля."""

    def __init__(self, portfolio: Portfolio, p_value: float = P_VALUE):
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
        blocks = [
            "\nОПТИМИЗАЦИЯ ПОРТФЕЛЯ",
            self._p_value_block(),
            f"{self.best_combination}",
        ]
        return "\n\n".join(blocks)

    def _p_value_block(self) -> str:
        """Информация значимости при множественном тестировании гипотез."""
        blocks = [
            "Оценка значимости:",
            f"forecasts = {self.n_forecasts}",
            f"p-value = {self.p_value:.2%}",
            f"trials = {self.trials}",
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

    @property
    def p_value(self) -> float:
        """Уровень значимости отклонения градиента от нуля."""
        return self._p_value

    @property
    def n_forecasts(self) -> int:
        """Количество прогнозов."""
        return self.metrics.count

    @property
    def trials(self) -> int:
        """Количество тестов на значимость.

        Продать можно позиции с не нулевым весом.

        Можно уйти в кэш или купить любую позицию, кроме продаваемой и с нулевым фактором объема.
        Для позиции с нулевым фактором объема - уйти в кеш или купить любую позицию кроме себя.
        """
        positions_to_sell = (self.portfolio.shares[:-2] > 0).sum()
        positions = len(self.portfolio.shares) - 2
        return positions_to_sell * positions - positions_to_sell + 1

    @property
    def best_combination(self):
        """Лучшие комбинации для торговли.

        Для каждого актива, который можно продать со значимым улучшением выбирается актив с
        максимальной вероятностью улучшения.
        """
        rez = self._wilcoxon_tests()

        rez = pd.DataFrame(
            list(rez),
            columns=[
                "SELL",
                "BUY",
                "RISK_CON",
                "R_DIFF",
                "TURNOVER",
                "P_VALUE",
            ],
        )
        rez = rez.sort_values(["RISK_CON", "R_DIFF"], ascending=[True, False])
        rez = rez.drop_duplicates("SELL")
        rez.index = pd.RangeIndex(start=1, stop=len(rez) + 1)

        return rez

    def _wilcoxon_tests(self) -> Tuple[str, str, float, float]:
        """Осуществляет тестирование всех допустимых пар активов с помощью теста Вилкоксона.

        Возвращает все значимо улучшающие варианты сделок в формате:

        - Продаваемый тикер
        - Покупаемый тикер
        - Медиана разницы в градиенте
        - Значимость скорректированная на общее количество тестов и оборачиваемость покупаемого тикера.
        """
        positions_to_sell = self.portfolio.index[:-2][self.portfolio.shares[:-2] > 0]
        positions_with_cash = self.portfolio.index[:-1]
        all_gradients = self.metrics.all_gradients
        betas = self.metrics.beta
        trials = self.trials
        turnover_all = self.portfolio.turnover_factor
        weight = self.portfolio.weight
        for sell, buy in itertools.product(positions_to_sell, positions_with_cash):

            if sell == buy or turnover_all[buy] == 0:
                continue

            factor = turnover_all[buy] - (weight[sell] + weight[CASH] - weight[buy]) / 2
            if factor < 0:
                continue

            diff = all_gradients.loc[buy] - all_gradients.loc[sell] - COSTS
            _, alfa = stats.wilcoxon(diff, alternative="greater", correction=True)

            alfa *= trials

            if alfa < P_VALUE:
                yield [
                    sell,
                    buy,
                    betas[buy] * weight[buy] - betas[sell] * weight[sell],
                    diff.median(),
                    factor,
                    alfa,
                ]
