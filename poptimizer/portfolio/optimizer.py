"""Оптимизатор портфеля."""
import math

import pandas as pd
from scipy import stats

from poptimizer.config import MAX_TRADE
from poptimizer.portfolio import metrics
from poptimizer.portfolio.portfolio import Portfolio, CASH, PORTFOLIO

# На сколько сделок разбивается операция по покупке/продаже акций
TRADES = 5
# Значимость отклонения градиента от нуля
P_VALUE = 0.05


class Optimizer:
    """Предлагает сделки для улучшения метрики портфеля."""

    def __init__(self, portfolio: Portfolio, p_value: float = P_VALUE):
        """Учитывается градиент, его ошибку и ликвидность бумаг - градиент корректирует на фактор
        оборота.

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
            self._buy_sell_block(),
            self._all_info_block(),
        ]
        return "\n\n".join(blocks)

    def _p_value_block(self) -> str:
        """Информация значимости при множественном тестировании гипотез."""
        blocks = [
            "Оценка значимости:",
            f"p_value = {self.p_value:.2%}",
            f"dof = {self.dof}",
            f"t-score {self.t_score:.2f}",
            f"trials = {self.trials}",
            f"Bonferroni t_score = {self.t_score_bonferroni:.2f}",
        ]
        return "\n".join(blocks)

    def _buy_sell_block(self) -> str:
        """Информация о лучшей покупке и продаже."""
        blocks = ["Лучшая сделка:", self._best_sell(), self._best_buy()]
        return "\n".join(blocks)

    def _best_sell(self) -> str:
        """Лучшая продажа."""
        upper_bound = self.upper_bound
        sell = -self.buy_sell
        upper_bound = upper_bound[sell.gt(0)]
        ticker = upper_bound.idxmin()
        return f"Продать {ticker} - {TRADES} сделок {sell[ticker]} лотов"

    def _best_buy(self) -> str:
        """Лучшая продажа."""
        lower_bound = self.lower_bound
        ticker = lower_bound.idxmax()
        return f"Купить  {ticker} - {TRADES} сделок {self.buy_sell[ticker]} лотов"

    def _all_info_block(self) -> str:
        """Сводная информация об оптимизации."""
        df = pd.concat(
            [
                self.gradient,
                self.turnover,
                self.lower_bound,
                self.adj_gradient,
                self.upper_bound,
                self.buy_sell.replace(0, ""),
            ],
            axis=1,
        )
        return str(df.sort_values(by="GRADIENT", axis=0, ascending=False))

    @property
    def portfolio(self) -> Portfolio:
        """Оптимизируемый портфель."""
        return self._portfolio

    @property
    def metrics(self) -> metrics.MetricsResample:
        """Метрики портфеля."""
        return self._metrics

    @property
    def gradient(self) -> pd.Series:
        """Градиент позиций."""
        return self._metrics.gradient

    @property
    def turnover(self) -> pd.Series:
        """Фактор оборота позиций."""
        return self._portfolio.turnover_factor

    @property
    def adj_gradient(self) -> pd.Series:
        """Градиент скорректированный на оборот.

        Для позиций с положительным градиентом он понижается на коэффициент оборота для учета
        неликвидности.
        """
        adj_gradient = self.gradient * self.turnover
        adj_gradient.name = "ADJ_GRAD"
        return adj_gradient

    @property
    def p_value(self) -> float:
        """Уровень значимости отклонения градиента от нуля."""
        return self._p_value

    @property
    def dof(self) -> int:
        """Количество степеней свободы в t-тесте."""
        return self.metrics.count - 1

    @property
    def t_score(self) -> float:
        """Базовый t-score до корректировки на множественное тестирование."""
        p_value = 1 - self.p_value / 2
        return stats.t.ppf(p_value, self.dof)

    @property
    def trials(self) -> int:
        """Количество тестов на значимость.

        Проверяются все позиции включая CASH, но исключая PORTFOLIO - портфель по определению имеет
        значение градиента равное 0.
        """
        return len(self.portfolio.index) - 1

    @property
    def t_score_bonferroni(self) -> float:
        """Скорректированный t-score с учетом поправки Бонферрони на множественное тестирование."""
        p_value = self.p_value / self.trials
        p_value = 1 - p_value / 2
        return stats.t.ppf(p_value, self.dof)

    @property
    def lower_bound(self) -> pd.Series:
        """Нижняя граница доверительного интервала градиента."""
        lower = self.adj_gradient - self._metrics.error.mul(self.t_score_bonferroni)
        lower.name = "LOWER"
        return lower

    @property
    def upper_bound(self) -> pd.Series:
        """Верхняя граница доверительного интервала градиента."""
        upper = self.adj_gradient + self._metrics.error.mul(self.t_score_bonferroni)
        upper.name = "UPPER"
        return upper

    @property
    def buy_sell(self) -> pd.Series:
        """Объемы продаж и покупок для позиций."""
        portfolio = self.portfolio
        lot_value_per_trades = (portfolio.price * portfolio.lot_size) * TRADES
        buy_sell = pd.Series(0, index=portfolio.index)

        value = portfolio.value
        buy_size = value[CASH] / lot_value_per_trades
        buy_size = buy_size.apply(lambda x: math.ceil(x))
        buy_sell = buy_sell.mask(self.lower_bound.gt(0), buy_size)

        max_trade = value[PORTFOLIO] * MAX_TRADE
        max_trade = max(0, max_trade - value[CASH])

        sell_size = max_trade / lot_value_per_trades
        sell_size = sell_size.apply(lambda x: math.ceil(x))

        buy_sell = buy_sell.mask(self.upper_bound.lt(0) & value.gt(0), -sell_size)
        buy_sell[CASH] = 0
        buy_sell.name = "BUY_SELL"
        return buy_sell
