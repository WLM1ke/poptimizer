"""Метки для обучения."""
from typing import Tuple

import pandas as pd

from poptimizer import data

YEAR_IN_TRADING_DAYS = 12 * 21
LABELS = "LABELS"


def make_labels(
    tickers: Tuple[str],
    date: pd.Timestamp,
    days: int = 21,
    normalize: int = YEAR_IN_TRADING_DAYS,
) -> pd.DataFrame:
    """Создает метки для машинного обучения - нормированный по СКО логарифм доходности.

    Доходность и СКО пересчитываются в годовое исчисление.

    :param tickers:
        Тикеры, для которых нужно создать метки.
    :param date:
        Дата, до которой нужно создать метки.
    :param days:
        За сколько дней считать доходность.
    :param normalize:
        За сколько дней считается СКО.
    :return:
        Данные:

            * Пересчитанная на год доходность.
            * Пересчитанное на год СКО.
            * Метки - отношение доходности к СКО.

        Многоуровневый индекс:

            * Первый уровень - дата
            * Второй уровень - тикер
    """
    returns = data.log_total_returns(tickers, date)
    mean = returns.rolling(days, min_periods=days).mean() * YEAR_IN_TRADING_DAYS
    std = returns.rolling(normalize, min_periods=days).std() * (
        YEAR_IN_TRADING_DAYS ** 0.5
    )
    index = returns.index[-1::-days]
    index = index[-1::-1]
    mean = mean.reindex(index).stack()
    std = std.reindex(index).stack()
    labels = pd.concat([mean, std], axis=1)
    labels.dropna(inplace=True)
    labels.columns = ["MEAN", "STD"]
    labels[LABELS] = labels["MEAN"] / labels["STD"]
    return labels
