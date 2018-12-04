"""Основные функции агригации данных, свезанных с котировками"""
import pandas as pd


def securities_info():
    pass


def lot_size(tickers: tuple):
    """Размер лотов для указанных акций

    :param tickers:
        Перечень тикеров акций
    :return:
        Размеры лотов
    """
    securities = securities_info()
    return securities.loc[list[tickers], "LOTSIZE"]


def prices(last_date: pd.Timestamp, tickers: tuple):
    """Пустые места должны быть заполнены предыдущими значениям - наличие даты проверено

    :param last_date:
    :param tickers:
    :return:
    """
    pass  # TODO
    return None


def turnovers(last_date: pd.Timestamp, tickers: tuple):
    """Пустые места должны быть заполнены предыдущими значениям - наличие даты проверено

    :param last_date:
    :param tickers:
    :return:
    """
    pass  # TODO
    return None
