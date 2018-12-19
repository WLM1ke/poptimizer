"""Поиск претендентов на включение и исключение из портфеля."""
import pandas as pd

from poptimizer import ml, data, portfolio
from poptimizer.config import ML_PARAMS
from poptimizer.ml import feature
from poptimizer.portfolio.portfolio import CASH


def feature_days(feat):
    """Поиск значения параметра количество дней для признака."""
    loc = ml.Examples.FEATURES.index(feat)
    return ML_PARAMS[0][loc][1]["days"]


def get_turnover(port, tickers):
    """Получает фактор оборота для тикеров."""
    date = port.date
    cash = port.shares[CASH]
    positions = {ticker: port.shares[ticker] for ticker in port.index[:-2]}
    for ticker in tickers:
        if ticker not in positions:
            positions[ticker] = 0
    all_tickers_port = portfolio.Portfolio(date, cash, positions)
    return all_tickers_port.turnover_factor[:-2]


def mark_not_portfolio(df, column_name, choose, current_port):
    """Выбирает лучшие и помечает бумаги не в портфеле."""
    df = df.sort_values(column_name, ascending=False)
    df = df.head(choose)
    df["ADD"] = "ADD"
    for ticker in current_port.index:
        if ticker in df.index:
            df.loc[ticker, "ADD"] = ""
    return df


def find_momentum(current_port: portfolio.Portfolio, part: float = 0.1) -> pd.DataFrame:
    """Поиск бумаг с устойчивым ростом и низкой волатильностью.

    Печатает, какие из входящих в лучшую часть бумаг не содержатся в текущем портфеле и могут быть
    в него добавлены.

    :param current_port:
        Текущий портфель.
    :param part:
        Доля всех котирующихся бумаг, которые должны быть выведены.
    :return:
        Сводная информация по лучшим акциям.
    """
    all_tickers = data.securities_with_reg_number()
    mean_days = feature_days(feature.Mean)
    date = current_port.date
    mean = feature.Mean(tuple(all_tickers), date).get(date, days=mean_days)
    mean *= mean_days
    std = feature.STD(tuple(all_tickers), date).get(date, days=mean_days)
    std *= mean_days ** 0.5
    df = pd.concat([mean, std], axis=1)
    df["TURNOVER"] = get_turnover(current_port, all_tickers)
    df["T_SCORE"] = df.iloc[:, 0] / df.iloc[:, 1] * df.iloc[:, 2]
    choose = int(part * all_tickers.size)
    df = mark_not_portfolio(df, "T_SCORE", choose, current_port)
    text = (
        f"\nПОИСК МОМЕНТУМ ТИКЕРОВ"
        f"\n"
        f"\nВсего с регистрационными номерами - {all_tickers.size} акций"
        f"\nВыведены {part:.0%} - {choose} акций"
        f"\n"
        f"\n{df}"
    )
    print(text)
    return df


def find_dividends(
    current_port: portfolio.Portfolio, part: float = 0.1
) -> pd.DataFrame:
    """Поиск бумаг с максимальными дивидендами.

    Печатает, какие из входящих в лучшую часть бумаг не содержатся в текущем портфеле и могут быть
    в него добавлены.

    :param current_port:
        Текущий портфель.
    :param part:
        Доля всех котирующихся бумаг, которые должны быть выведены.
    :return:
        Сводная информация по лучшим акциям.
    """
    all_tickers = data.securities_with_reg_number()
    div_days = feature_days(feature.Dividends)
    date = current_port.date
    div = feature.Dividends(tuple(all_tickers), date).get(date, days=div_days)
    div = div.to_frame()
    div["TURNOVER"] = get_turnover(current_port, all_tickers)
    div["SCORE"] = div.iloc[:, 0] * div.iloc[:, 1]
    choose = int(part * all_tickers.size)
    div = mark_not_portfolio(div, "SCORE", choose, current_port)
    text = (
        f"\nПОИСК ДИВИДЕНДНЫХ ТИКЕРОВ"
        f"\n"
        f"\nВсего с регистрационными номерами - {all_tickers.size} акций"
        f"\nВыведены {part:.0%} - {choose} акций"
        f"\n"
        f"\n{div}"
    )
    print(text)
    return div


def find_zero_turnover_and_weight(current_port: portfolio.Portfolio):
    """Ищет бумаги с нулевым оборотом и весом - потенциальные цели для исключения."""
    zero_weight = current_port.weight == 0
    zero_turnover = current_port.turnover_factor == 0
    zero = list(current_port.index[zero_weight & zero_turnover])
    print("\nБУМАГИ С НУЛЕВЫМ ОБОРОТОМ И ВЕСОМ")
    print()
    print(*zero)
    return zero
