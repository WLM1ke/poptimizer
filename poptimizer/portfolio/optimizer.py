"""Оптимизатор портфеля."""
import os
from datetime import datetime
import numpy as np
import pandas as pd
from scipy import stats
from sklearn.preprocessing import quantile_transform

from poptimizer import config
from poptimizer.portfolio import metrics
from poptimizer.portfolio.excel_format import save_to_excel
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
        rec = self._for_trade()
        forecasts = self.metrics.count
        blocks = [
            "\nОПТИМИЗАЦИЯ ПОРТФЕЛЯ",
            f"\nforecasts = {forecasts}",
            f"p-value = {self._p_value:.2%}",
            f"\n{rec['SELL']}",
            f"\n{rec['BUY']}",
            f"\n{rec['new_port_summary']}",
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

    def _update_portfolio(self, rec, cash):
        # создаём новый портфель с учётом этой транзакции
        rec['SHARES'] = rec['lots'] * rec['lot_size']
        cur_prot = Portfolio(name=self.portfolio.name,
                             date=self.portfolio.date,
                             cash=cash,
                             positions=rec['SHARES'].to_dict())
        return cur_prot

    def _for_trade(self, serialize=True) -> pd.DataFrame:
        """Осуществляет расчет рекомендуемых операций."""
        cur_prot = self.portfolio
        rec = None
        op = None
        ports_set = set()
        while True:
            cur_metrics = metrics.MetricsResample(cur_prot)
            grads = cur_metrics.all_gradients.iloc[:-2]
            # гармоническое среднее квантилей градиентов вместо PRIORITY

            rec = pd.Series(data=stats.hmean(quantile_transform(grads, n_quantiles=grads.shape[0]), axis=1),
                            index=grads.index).to_frame(name='PRIORITY')
            rec.sort_values(["PRIORITY"], ascending=[False], inplace=True)
            rec['lot_size'] = cur_prot.lot_size.loc[rec.index]
            rec['lots'] = (cur_prot.shares.loc[rec.index] / rec['lot_size']).fillna(0).astype(int)
            rec['lot_price'] = (cur_prot.lot_size.loc[rec.index] * cur_prot.price.loc[rec.index]).round(2)

            top_share = rec.index[0]
            bot_share = rec.loc[rec['lots'] > 0].index[-1]
            cash = cur_prot.value[CASH] + self.portfolio.value['PORTFOLIO'] - cur_prot.value['PORTFOLIO']
            if cash > rec.loc[top_share, 'lot_price']:
                rec.loc[top_share, 'lots'] += 1
                cash -= rec.loc[top_share, 'lot_price']
                op = ('BUY', top_share)
            else:
                rec.loc[bot_share, 'lots'] -= 1
                cash += rec.loc[bot_share, 'lot_price']
                op = ('SELL', bot_share)
            cur_prot = self._update_portfolio(rec, cash)
            print(op, cash)
            port_tuple = tuple(cur_prot.shares.drop(CASH).tolist())
            # проверка цикла
            if port_tuple in ports_set:
                break
            ports_set.add(port_tuple)
            if len(ports_set) % 1000 == 0:
                print('ITERATION', len(ports_set), self.portfolio.name)

        rec['SUM'] = (rec['lots'] * rec['lot_price']).round(2)
        rec.sort_values('SUM', ascending=False, inplace=True)
        rec['lots_exists'] = (self.portfolio.shares.loc[rec.index] / rec['lot_size']).fillna(0).astype(int)
        rec['SHARES_AFTER'] = rec['lots'] * rec['lot_size']
        recommendations = dict()
        recommendations['SELL'] = rec.loc[rec['lots'] < rec['lots_exists']].copy()
        recommendations['SELL']['lots'] = recommendations['SELL']['lots_exists'] - recommendations['SELL']['lots']

        recommendations['BUY'] = rec.loc[rec['lots'] > rec['lots_exists']].copy()
        recommendations['BUY']['lots'] = recommendations['BUY']['lots'] - recommendations['BUY']['lots_exists']

        for op in ['SELL', 'BUY']:
            recommendations[op]['SHARES'] = recommendations[op]['lots'] * recommendations[op]['lot_size']
            recommendations[op]['SHARES_exists'] = recommendations[op]['lots_exists'] * recommendations[op]['lot_size']
            # корректируем сумму учитывая целое количество лотов
            recommendations[op]['SUM'] = (recommendations[op]['lots'] * recommendations[op]['lot_price']).round(2)

            recommendations[op] = recommendations[op][['lot_size', 'lot_price', 'SHARES_exists', 'lots_exists',
                                                       'lots', 'SHARES', 'SUM', 'SHARES_AFTER']]
            recommendations[op].rename({'lots': f'lots_to_{op}'}, inplace=True, axis='columns')
            recommendations[op].rename({'SHARES': f'SHARES_to_{op}'}, inplace=True, axis='columns')
            recommendations[op].rename({'SUM': f'SUM_to_{op}'}, inplace=True, axis='columns')

        recommendations['new_port_summary'] = cur_prot._main_info_df()
        if serialize:
            path = f"{config.REPORTS_PATH}/{'/'.join(self.portfolio.name)}"
            print(path)
            os.makedirs(path, exist_ok=True)
            save_to_excel(f"{path}/{str(datetime.today())[:10]}_{','.join(self.portfolio.name)}.xlsx",
                          {'summary': self.portfolio._main_info_df(),
                           'lots_to_sell': recommendations['SELL'],
                           'lots_to_buy': recommendations['BUY'],
                           'new_port_summary': recommendations['new_port_summary']}
                          )
        return recommendations

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
