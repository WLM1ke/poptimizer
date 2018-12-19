"""Поиск бумаг с устойчивым ростом и низкой волатильностью."""
import pandas as pd

from poptimizer import ml, data
from poptimizer.config import ML_PARAMS
from poptimizer.ml import feature
from poptimizer.portfolio import Portfolio

BEST_SHARE = 0.1


def find_momentum(portfolio: Portfolio):
    """Поиск бумаг с устойчивым ростом и низкой волатильностью."""
    all_tickers = data.securities_with_reg_number()
    mean_loc = ml.Examples.FEATURES.index(feature.Mean)
    mean_days = ML_PARAMS[0][mean_loc][1]["days"]
    date = portfolio.date
    mean = feature.Mean(tuple(all_tickers), date).get(date, days=mean_days)
    mean *= mean_days
    std = feature.STD(tuple(all_tickers), date).get(date, days=mean_days)
    std *= mean_days ** 0.5
    df = pd.concat([mean, std], axis=1)
    positions = {ticker: 1 for ticker in all_tickers}
    df["TURNOVER"] = Portfolio(portfolio.date, 0, positions).turnover_factor
    df["T_SCORE"] = df.iloc[:, 0] / df.iloc[:, 1] * df.iloc[:, 2]
    df = df.sort_values("T_SCORE", ascending=False)
    df = df.head(int(BEST_SHARE * all_tickers.size))
    df["ADD"] = "ADD"
    for ticker in portfolio.index:
        if ticker in df.index:
            df.loc[ticker, "ADD"] = ""
    text = (
        f"\nПОИСК МОМЕНТУМ ТИКЕРОВ"
        f"\n\n"
        f"Всего акций с регистрационными номерами - {all_tickers.size}"
        f"\n\n"
        f"{df}"
    )
    print(text)
