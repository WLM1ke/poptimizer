"""Поиск бумаг с устойчивым ростом и низкой волатильностью."""
import pandas as pd

from poptimizer import ml, data, portfolio
from poptimizer.config import ML_PARAMS
from poptimizer.ml import feature


def find_momentum(current_port: portfolio.Portfolio, part: float = 0.1):
    """Поиск бумаг с устойчивым ростом и низкой волатильностью.

    Печатает, какие из входящих в лучшую часть бумаг не содержатся в текущем портфеле и могут быть
    в него добавлены.

    :param current_port:
        Текущий портфель.
    :param part:
        Доля всех котирующихся бумаг, которые должны быть выведены.
    """
    all_tickers = data.securities_with_reg_number()
    mean_loc = ml.Examples.FEATURES.index(feature.Mean)
    mean_days = ML_PARAMS[0][mean_loc][1]["days"]
    date = current_port.date
    mean = feature.Mean(tuple(all_tickers), date).get(date, days=mean_days)
    mean *= mean_days
    std = feature.STD(tuple(all_tickers), date).get(date, days=mean_days)
    std *= mean_days ** 0.5
    df = pd.concat([mean, std], axis=1)
    positions = {ticker: 1 for ticker in all_tickers}
    all_tickers_port = portfolio.Portfolio(date, 0, positions)
    df["TURNOVER"] = all_tickers_port.turnover_factor
    df["T_SCORE"] = df.iloc[:, 0] / df.iloc[:, 1] * df.iloc[:, 2]
    df = df.sort_values("T_SCORE", ascending=False)
    choose = int(part * all_tickers.size)
    df = df.head(choose)
    df["ADD"] = "ADD"
    for ticker in current_port.index:
        if ticker in df.index:
            df.loc[ticker, "ADD"] = ""
    text = (
        f"\nПОИСК МОМЕНТУМ ТИКЕРОВ"
        f"\n"
        f"\nВсего с регистрационными номерами - {all_tickers.size} акций"
        f"\nВыведены {part:.0%} - {choose} акций"
        f"\n"
        f"\n{df}"
    )
    print(text)
