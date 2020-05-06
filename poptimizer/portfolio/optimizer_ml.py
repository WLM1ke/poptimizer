"""Оптимизатор портфеля."""
import pandas as pd

from poptimizer import config
from poptimizer.config import MAX_TRADE
from poptimizer.portfolio import metrics_ml
from poptimizer.portfolio.portfolio import PORTFOLIO, CASH, Portfolio

DAYS_IN_MONTH = 21

# На сколько сделок разбивается операция по покупке/продаже акций
TRADES = 5


class Optimizer:
    """Предлагает сделки для улучшения метрик портфеля.

    Учитывается градиент и ликвидность бумаг - градиент корректирует на фактор оборота.
    Возможное улучшение сравнивается с СКО градиента.
    """

    def __init__(
        self,
        portfolio: Portfolio,
        months: float = config.ML_PARAMS["data"][0][1]["days"] / DAYS_IN_MONTH,
    ):
        """Портфель оптимизируется с учетом метрик для определенного периода времени.

        По умолчанию период оптимизации равен периоду прогнозирования доходности.

        :param portfolio:
            Оптимизируемый портфель.
        :param months:
            Период времени для расчета метрик.
        """
        self._portfolio = portfolio
        self._metrics = metrics_ml.Metrics(portfolio, months)

    def __str__(self) -> str:
        recommendation = self._trade_recommendation()
        df = self._main_stat()
        return f"\nОПТИМИЗАЦИЯ ПОРТФЕЛЯ\n{recommendation}\n\n{df}"

    def _trade_recommendation(self) -> str:
        portfolio = self.portfolio
        trade_size = portfolio.value[PORTFOLIO] * MAX_TRADE
        cash = portfolio.value[CASH]
        best_sell = self.best_sell
        sell_lots = (
            (trade_size - cash)
            / portfolio.price[best_sell]
            / portfolio.lot_size[best_sell]
        )
        sell_lots = max(1, int(min(sell_lots, portfolio.lots[best_sell]) / TRADES))
        best_buy = self.best_buy
        buy_lots = cash / portfolio.price[best_buy] / portfolio.lot_size[best_buy]
        buy_lots = max(1, int(buy_lots / TRADES))
        return (
            f"\nЛУЧШАЯ СДЕЛКА"
            f"\nt_score = {self.gradient_growth[self.best_buy] / self.metrics.std_gradient:.2f}"
            f"\nПродать {best_sell} - {TRADES} сделок {sell_lots} лотов"
            f"\nКупить  {best_buy} - {TRADES} сделок {buy_lots} лотов"
        )

    def _main_stat(self) -> str:
        metrics_ = self.metrics
        df = pd.concat(
            [
                metrics_.lower_bound,
                metrics_.gradient,
                self.portfolio.turnover_factor,
                self.gradient_growth,
            ],
            axis=1,
        )
        df.columns = ["LOWER_BOUND", "GRADIENT", "TURNOVER", "GROWTH"]
        return df.sort_values("LOWER_BOUND", ascending=False)

    @property
    def portfolio(self) -> Portfolio:
        """Оптимизируемый портфель."""
        return self._portfolio

    @property
    def metrics(self) -> metrics_ml.Metrics:
        """Метрика, используемая для оптимизации."""
        return self._metrics

    @property
    def best_sell(self) -> str:
        """Бумага с не нулевым объемом и минимальным градиентом."""
        # noinspection PyTypeChecker
        non_zero_holdings = self.portfolio.shares > 0
        # noinspection PyUnresolvedReferences
        non_zero_holdings.loc[[CASH, PORTFOLIO]] = False
        return self.metrics.gradient[non_zero_holdings].idxmin()

    @property
    def gradient_growth(self) -> pd.Series:
        """Возможный прирост градиента с поправкой на объем."""
        gradient = self.metrics.gradient
        min_gradient = gradient[self.best_sell]
        return (gradient - min_gradient) * self.portfolio.turnover_factor

    # noinspection PyTypeChecker
    @property
    def best_buy(self) -> str:
        """Бумага с максимальным ростом градиента с поправкой на оборот."""
        return self.gradient_growth.idxmax()
