"""Оптимизатор портфеля."""
import numpy as np
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
        conf_int["COSTS"] = self._costs()
        conf_int["PRIORITY"] = conf_int["LOWER"] - conf_int["COSTS"]

        for_sale = conf_int["UPPER"] < 0
        for_sale = for_sale & (self._portfolio.shares.iloc[:-2] > 0)  # noqa: WPS465
        for_sale = conf_int[for_sale]
        for_sale = for_sale.assign(PRIORITY=lambda df: df["UPPER"])

        good_purchase = conf_int["PRIORITY"] > 0  # noqa: WPS465
        good_purchase = conf_int[good_purchase]

        return pd.concat(
            [
                good_purchase,
                for_sale,
            ],
            axis=0,
        ).sort_values("PRIORITY", ascending=False)

    def _costs(self) -> pd.DataFrame:
        """Удельные торговые издержки.

        Полностью распределяются на покупаемую позицию с учетом ее последующего закрытия. Состоят из
        двух составляющих - комиссии и воздействия на рынок. Для учета воздействия на рынок
        используется Rule of thumb, trading one day’s volume moves the price by about one day’s
        volatility

        https://arxiv.org/pdf/1705.00109.pdf

        Размер операций на покупку условно выбран равным текущему кэшу, а на последующую продажу
        текущая позиция плюс кэш за вычетом уже учтенных издержек на продажу текущей позиции.

        Было решено отказаться от расчета производной так как для нулевых позиций издержки воздействия
        небольшие, но быстро нарастают с объемом. Расчет для условной сделки в размере кэша сразу
        отсекает совсем неликвидных кандидатов на покупку.
        """
        port = self._portfolio

        cash = port.weight[CASH] / port.turnover_factor
        weight = port.weight / port.turnover_factor
        weight_cash = weight + cash

        impact_scale = 1.5

        return (
            # Размер рыночного воздействие в дневном СКО для дневного оборот
            config.MARKET_IMPACT_FACTOR
            # Дневное СКО
            * (self.metrics.std / config.YEAR_IN_TRADING_DAYS ** 0.5)
            # Зависимость общих издержек от воздействия пропорционален степени 1.5 от нормированного на
            # дневной оборот объема. Совершается покупка на кэш сейчас и увеличиваются издержки на
            # ликвидацию позиции
            * (cash ** impact_scale + (weight_cash ** impact_scale - weight ** impact_scale))
            # Делим на объем операции для получения удельных издержек
            / cash
            # Умножаем на коэффициент пересчета в годовые значения
            * (config.YEAR_IN_TRADING_DAYS / config.FORECAST_DAYS)
            # Обычные издержки в две стороны
            + config.COSTS * 2
        )


def _grad_conf_int(forecasts, p_value) -> tuple[float, float]:
    interval = stats.bootstrap(
        (forecasts,),
        np.median,
        confidence_level=(1 - p_value),
        random_state=0,
    ).confidence_interval

    return interval.low, interval.high
