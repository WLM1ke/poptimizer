"""Формирует прогноз по всем моделям в популяции."""
from collections.abc import Iterable
from typing import Tuple, Iterator

import numpy as np
import pandas as pd
import tqdm

from poptimizer import data, store
from poptimizer.config import YEAR_IN_TRADING_DAYS
from poptimizer.dl import DegeneratedForecastError
from poptimizer.evolve import population, ledoit_wolf

# Ключ для хранений кеша прогноза
FORECAST = "dl"


def ledoit_wolf_cov(
    tickers: tuple, date: pd.Timestamp
) -> Tuple[np.array, float, float]:
    """Ковариационная матрица на основе Ledoit Wolf и вспомогательные данные.

    Оригинальная матрица корректируется в сторону не смещенной оценки на малой выборке и точность
    ML-прогноза.
    """
    div, p1 = data.div_ex_date_prices(tickers, date)
    p0 = p1.shift(1)
    returns = (p1 + div) / p0
    returns = returns.iloc[-YEAR_IN_TRADING_DAYS:]
    returns = (returns - returns.mean()) / returns.std(ddof=0)
    return ledoit_wolf.shrinkage(returns.values)


class Forecasts(Iterable):
    """Прогнозы доходности и ковариационной матрицы для DL-моделей."""

    def __init__(self, tickers: Tuple[str, ...], date: pd.Timestamp):
        self._tickers = tickers
        self._date = date

        sigma, self._average_cor, self._shrink = ledoit_wolf_cov(tickers, date)
        self._forecasts = []
        for organism in tqdm.tqdm(population.get_all_organisms(), desc="Forecasts"):
            try:
                m, s = organism.forecast(tickers, date)
            except DegeneratedForecastError:
                continue
            s = s.values
            s = s.reshape(1, -1) * sigma * s.reshape(-1, 1)
            self._forecasts.append((m, s))

    def __iter__(self) -> Iterator[Tuple[pd.Series, np.array]]:
        yield from self._forecasts

    @property
    def tickers(self) -> Tuple[str, ...]:
        """Для каких тикеров составлен прогноз."""
        return self._tickers

    @property
    def date(self) -> pd.Timestamp:
        """На какую дату составлен прогноз."""
        return self._date

    @property
    def average_cor(self) -> float:
        """Средняя корреляция акций."""
        return self._average_cor

    @property
    def shrink(self) -> float:
        """Сила сжатия."""
        return self._shrink


def get_forecasts(tickers: Tuple[str, ...], date: pd.Timestamp) -> Forecasts:
    """Создает или загружает закешированный прогноз для набора тикеров на указанную дату.

    :param tickers:
        Тикеры, для которых необходимо составить прогноз.
    :param date:
        Дата, на которую нужен прогноз.
    :return:
        Прогнозная доходность, ковариация и дополнительная информация.
    """
    mongodb = store.MongoDB()
    forecast_cache = mongodb[FORECAST]
    if (
        forecast_cache is not None
        and forecast_cache.date == date
        and forecast_cache.tickers == tickers
    ):
        return forecast_cache
    forecast = Forecasts(tickers, date)
    mongodb[FORECAST] = forecast
    return forecast
