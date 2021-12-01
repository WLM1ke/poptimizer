"""Оптимизатор портфеля на основе ресемплирования отдельных прогнозов."""
import numpy as np
import pandas as pd
from scipy import stats

from poptimizer import config
from poptimizer.portfolio import metrics
from poptimizer.portfolio.portfolio import CASH, Portfolio

# Наименование столбцов
_PRIORITY = "PRIORITY"
_LOWER = "LOWER"
_UPPER = "UPPER"
_COSTS = "COSTS"
_SELL = "SELL"
_BUY = "BUY"
_SIGNAL = "SIGNAL"
_WEIGHT = "WEIGHT"
_RISK_CON = "RISK_CON"


class Optimizer:  # noqa: WPS214
    """Предлагает сделки для улучшения метрики портфеля.

    Использует множество предсказаний и статистические тесты для выявления только статистически значимых
    улучшений портфеля, которые покрывают транзакционные издержки и импакт на рыночные котировки.
    Рекомендации даются в сокращенном виде без конкретизации конкретных сделок.
    """

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
            f"impact = {config.MARKET_IMPACT_FACTOR:.2f}",
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
        conf_int = self._prepare_bounds()

        break_even = self._break_even(conf_int)

        sell = self._select_sell(conf_int, break_even)

        bye = self._select_buy(break_even, conf_int)

        rez = pd.concat([bye, sell], axis=0)
        rez = rez.sort_values(_PRIORITY, ascending=False)
        rez[_PRIORITY] = rez[_PRIORITY] - break_even

        return rez

    def _break_even(self, conf_int):
        non_zero_positions = self._portfolio.shares.iloc[:-2] > 0

        return conf_int[_UPPER].loc[non_zero_positions].min()

    def _select_buy(self, break_even, conf_int):
        buy = conf_int[_PRIORITY] >= break_even  # noqa: WPS465
        buy = conf_int[buy]
        kwarg = {_SIGNAL: lambda df: _BUY}

        return buy.assign(**kwarg)

    def _select_sell(self, conf_int, break_even):
        sell = conf_int[_UPPER] <= break_even
        sell = sell & (self._portfolio.shares.iloc[:-2] > 0)  # noqa: WPS465
        sell = conf_int[sell]
        kwarg = {
            _PRIORITY: lambda df: df[_UPPER],
            _SIGNAL: lambda df: _SELL,
        }

        return sell.assign(**kwarg)

    def _prepare_bounds(self):
        p_value = self._p_value / (len(self._portfolio.index) - 2) * 2
        conf_int = self.metrics.all_gradients.iloc[:-2]
        conf_int = conf_int.apply(
            lambda grad: _grad_conf_int(grad, p_value),
            axis=1,
            result_type="expand",
        )

        risk_contribution = self._metrics.beta[:-2]
        risk_contribution = risk_contribution * self._portfolio.weight.iloc[:-2]

        conf_int = pd.concat(
            [
                self._portfolio.weight.iloc[:-2],
                risk_contribution,
                conf_int,
            ],
            axis=1,
        )
        conf_int.columns = [_WEIGHT, _RISK_CON, _LOWER, _UPPER]
        conf_int[_COSTS] = self._costs()
        conf_int[_PRIORITY] = conf_int[_LOWER] - conf_int[_COSTS]

        return conf_int

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
    forecasts = (forecasts,)
    interval = stats.bootstrap(
        forecasts,
        np.median,
        confidence_level=(1 - p_value),
        random_state=0,
    ).confidence_interval

    return interval.low, interval.high
