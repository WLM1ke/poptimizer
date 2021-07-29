"""Оптимизатор портфеля."""
import pandas as pd
from scipy import stats

from poptimizer import config
from poptimizer.portfolio import metrics
from poptimizer.portfolio.portfolio import CASH, Portfolio


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
        """Информация о позициях, градиенты которых значимо отличны от 0."""
        df = self._for_trade()
        forecasts = self.metrics.count
        blocks = [
            "\nОПТИМИЗАЦИЯ ПОРТФЕЛЯ",
            f"\nforecasts = {forecasts}",
            f"p-value = {self._p_value:.2%}",
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

    def _for_trade(self) -> pd.DataFrame:
        """Осуществляет расчет доверительного интервала для среднего."""
        p_value = self._p_value / (len(self._portfolio.index) - 2)

        conf_int = self.metrics.all_gradients.iloc[:-2]
        conf_int = conf_int.apply(
            lambda grad: _grad_conf_int(grad, p_value),
            axis=1,
            result_type="expand",
        )
        conf_int.columns = ["LOWER", "UPPER"]

        portfolio = self._portfolio

        for_sale = conf_int["UPPER"] < -config.COSTS
        for_sale = for_sale & (portfolio.shares.iloc[:-2] > 0)  # noqa: WPS465
        for_sale = conf_int[for_sale]

        good_purchase = portfolio.turnover_factor.iloc[:-2] > portfolio.weight[CASH]
        good_purchase = good_purchase & (conf_int["LOWER"] > config.COSTS)  # noqa: WPS465
        good_purchase = conf_int[good_purchase]

        return pd.concat(
            [
                good_purchase.sort_values("LOWER", ascending=False),
                for_sale.sort_values("UPPER", ascending=False),
            ],
            axis=0,
        )


def _grad_conf_int(forecasts, p_value) -> tuple[float, float]:
    return stats.bayes_mvs(forecasts, (1 - p_value))[0][1]
