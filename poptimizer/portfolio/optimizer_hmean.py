"""Оптимизатор портфеля на основе рангов отдельных акций и гармонического среднего прогнозов."""
import logging
import numpy as np
import pandas as pd
from scipy import stats
from sklearn.preprocessing import quantile_transform

from poptimizer.portfolio import metrics
from poptimizer.portfolio.portfolio import CASH, Portfolio


class Optimizer:
    """Предлагает сделки для улучшения метрики портфеля.

    Использует ранги преимуществ бумаг для сглаживания выбросов по отдельным бумагам и гармоническую
    среднюю между различными прогнозами, при этом не учитываются транзакционные издержки и импакт на
    рыночные котировки. В результате даются детальные рекомендации с конкретными сделками. Для большого
    портфеля оптимизация может занять много времени.
    """

    def __init__(self, portfolio: Portfolio, wl_portfolio: Portfolio = None):
        """Учитывается градиент, его ошибку и ликвидность бумаг.

        :param portfolio:
            Оптимизируемый портфель.
        :param wl_portfolio:
            Портфель, содержащий список всех допустимых тикеров (white list), используется для фильтрации рекомендаций.
        """
        self._portfolio = portfolio
        self._wl_portfolio = wl_portfolio
        self._metrics = metrics.MetricsResample(portfolio)
        self._logger = logging.getLogger()
        self.rec = None

    def __str__(self) -> str:
        """Информация о позициях, градиенты которых значимо отличны от 0."""
        if self.rec is None:
            self.rec = self._for_trade()
        forecasts = self.metrics.count
        blocks = [
            "\nОПТИМИЗАЦИЯ ПОРТФЕЛЯ",
            f"\nforecasts = {forecasts}",
            f"\n{self.rec['SELL']}",
            f"\n{self.rec['BUY']}",
            f"\n{self.rec['new_port_summary']}",
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
        """Создаёт новый портфель с учётом новой транзакции"""
        rec["SHARES"] = rec["lots"] * rec["LOT_size"]
        cur_prot = Portfolio(
            name=self.portfolio.name,
            date=self.portfolio.date,
            cash=cash,
            positions=rec["SHARES"].to_dict(),
        )
        return cur_prot

    def _for_trade(self) -> dict[str, pd.DataFrame]:
        """Осуществляет расчет рекомендуемых операций."""
        self._logger.info("\nОПТИМИЗАЦИЯ ПОРТФЕЛЯ\n")

        cur_prot = self.portfolio
        rec, op = None, None
        # используется для определения цикла в операциях (получение портфеля который был ранее)
        ports_set = set()
        while True:
            cur_metrics = metrics.MetricsResample(cur_prot)
            grads = cur_metrics.all_gradients.iloc[:-2]
            # гармоническое среднее квантилей градиентов вместо бутстрапа
            # вычислительно существенно быстрее
            q_trans_grads = quantile_transform(grads, n_quantiles=grads.shape[0])
            # обработка (маскировка) возможных NA от плохих моделей
            q_trans_grads = np.ma.array(q_trans_grads, mask=~(q_trans_grads > 0))
            # гармоническое среднее сильнее штрафует за низкие значения (близкие к 0),
            # но его использование не принципиально - можно заменить на просто среднее или медиану
            hmean_q_trans_grads = stats.hmean(q_trans_grads, axis=1)
            rec = pd.Series(data=hmean_q_trans_grads, index=grads.index).to_frame(name="PRIORITY")
            rec.sort_values(["PRIORITY"], ascending=[False], inplace=True)

            # так как все операции производятся в лотах, нужно знать стоимость лота и текущее количество лотов
            rec["LOT_size"] = cur_prot.lot_size.loc[rec.index]
            rec["lots"] = (cur_prot.shares.loc[rec.index] / rec["LOT_size"]).fillna(0).astype(int)
            rec["LOT_price"] = (cur_prot.lot_size.loc[rec.index] * cur_prot.price.loc[rec.index]).round(
                2
            )

            rec['is_acceptable'] = True
            if self._wl_portfolio is not None:
                # помечаем все тикеры, которых нет в white list portfolio
                # также продаём все недопустимые позиции
                banned_tickers = rec.index.difference(self._wl_portfolio.index)
                rec.loc[banned_tickers, 'is_acceptable'] = False
                rec.loc[banned_tickers, 'lots'] = 0

            cash = cur_prot.value[CASH] + self.portfolio.value["PORTFOLIO"] - cur_prot.value["PORTFOLIO"]

            # определяем операцию:
            # покупка, если на покупку лучшего тикера хватает CASH
            # иначе - продажа худшго тикера из тех, что в наличии

            top_share = rec.loc[rec['is_acceptable']].index[0]
            bot_share = rec.loc[rec["lots"] > 0].index[-1]
            if cash > rec.loc[top_share, "LOT_price"]:
                rec.loc[top_share, "lots"] += 1
                cash -= rec.loc[top_share, "LOT_price"]
                op = ("BUY", top_share)
            else:
                rec.loc[bot_share, "lots"] -= 1
                cash += rec.loc[bot_share, "LOT_price"]
                op = ("SELL", bot_share)
            cur_prot = self._update_portfolio(rec, cash)
            log_str = '\t'.join([f'{str(len(ports_set) + 1): <7}',
                                 f'{op[0]: <4}', f'{op[1]: <7}',
                                 f"PRIORITY: {rec.loc[op[1], 'PRIORITY']:.3f}",
                                 f"CASH: {cash:.0f}"])
            self._logger.info(log_str)
            # проверка цикла
            port_tuple = tuple(cur_prot.shares.drop(CASH).tolist())
            if port_tuple in ports_set:
                break
            ports_set.add(port_tuple)

        # оптимизированный портфель получен
        # сортируем по новому весу от портфеля для наглядности и приоритезации сделок на покупку
        rec["SUM"] = (rec["lots"] * rec["LOT_price"]).round(2)
        rec.sort_values("SUM", ascending=False, inplace=True)
        # найдем разницу с текущим портфелем
        rec["LOTS_exists"] = (
            (self.portfolio.shares.loc[rec.index] / rec["LOT_size"]).fillna(0).astype(int)
        )
        rec["SHARES_after"] = rec["lots"] * rec["LOT_size"]
        report = dict()
        report["current_port_summary"] = self.portfolio._main_info_df()

        report["SELL"] = rec.loc[rec["lots"] < rec["LOTS_exists"]].copy()
        report["SELL"]["lots"] = report["SELL"]["LOTS_exists"] - report["SELL"]["lots"]

        report["BUY"] = rec.loc[rec["lots"] > rec["LOTS_exists"]].copy()
        report["BUY"]["lots"] = report["BUY"]["lots"] - report["BUY"]["LOTS_exists"]

        report["new_port_summary"] = cur_prot._main_info_df()

        for op in ["SELL", "BUY"]:
            report[op]["SHARES"] = report[op]["lots"] * report[op]["LOT_size"]
            report[op]["SHARES_exists"] = report[op]["LOTS_exists"] * report[op]["LOT_size"]
            # корректируем сумму учитывая целое количество лотов
            report[op]["SUM"] = (report[op]["lots"] * report[op]["LOT_price"]).round(2)
            # изменение порядка столбцов
            report[op] = report[op][
                [
                    "LOT_size",
                    "LOT_price",
                    "SHARES_exists",
                    "LOTS_exists",
                    "lots",
                    "SHARES",
                    "SUM",
                    "SHARES_after",
                ]
            ]
            report[op].rename(
                {"lots": f"LOTS_to_{op}", "SHARES": f"SHARES_to_{op}", "SUM": f"SUM_to_{op}"},
                inplace=True,
                axis="columns",
            )
        return report
