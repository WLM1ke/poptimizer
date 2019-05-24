"""Поиск претендентов на включение и исключение из портфеля."""
import pandas as pd

from poptimizer import data, portfolio, config
from poptimizer.portfolio import optimizer
from poptimizer.portfolio.portfolio import CASH, Portfolio


def feature_params(feat_name):
    """Поиск значения параметра количество дней для признака."""
    feat_conf = config.ML_PARAMS["data"]
    (_, params), *_ = filter(lambda x: x[0] == feat_name, feat_conf)
    return params


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


def mark_not_portfolio(df, column_name, current_port, choose=None):
    """Выбирает лучшие и помечает бумаги не в портфеле."""
    df = df.sort_values(column_name, ascending=False)
    if choose:
        df = df.head(choose)
    df["ADD"] = "ADD"
    for ticker in current_port.index:
        if ticker in df.index:
            df.loc[ticker, "ADD"] = ""
    return df


def find_good_volume(current_port: Portfolio) -> pd.DataFrame:
    """Поиск бумаг с не нулевым фактором объема.

    Печатает, какие не содержатся в текущем портфеле и могут быть в него добавлены.

    :param current_port:
        Текущий портфель.
    :return:
        Сводная информация по лучшим акциям.
    """
    all_tickers = data.securities_with_reg_number()
    df = get_turnover(current_port, all_tickers)
    df = df[df > 0]
    df.sort_values(ascending=False, inplace=True)
    df = df.to_frame("VOLUME")
    return mark_not_portfolio(df, "VOLUME", current_port)


def find_zero_turnover_and_weight(current_port: Portfolio):
    """Ищет бумаги с нулевым оборотом и весом - потенциальные цели для исключения."""
    zero_weight = current_port.weight == 0
    zero_turnover = current_port.turnover_factor == 0
    return list(current_port.index[zero_weight & zero_turnover])


def add_tickers(current_port: Portfolio):
    """Претенденты для добавления."""
    print(f"\nМОМЕНТУМ ТИКЕРЫ\n\n{find_good_volume(current_port)}")


def remove_tickers(opt: optimizer.Optimizer):
    """Претенденты на удаление."""
    print(
        f"\nБУМАГИ С НУЛЕВЫМ ОБОРОТОМ И ВЕСОМ"
        f"\n"
        f"\n{find_zero_turnover_and_weight(opt.portfolio)}"
    )
