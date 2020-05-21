"""Формирует прогноз по всем моделям в популяции."""
from collections.abc import Iterable
from typing import Tuple, Iterator

import numpy as np
import pandas as pd
import tqdm

from poptimizer import store
from poptimizer.evolve import population

# Ключ для хранений кеша прогноза
from poptimizer.evolve.population import ForecastError

FORECAST = "dl"


class Forecasts(Iterable):
    """Прогнозы доходности и ковариационной матрицы для DL-моделей."""

    def __init__(self, tickers: Tuple[str, ...], date: pd.Timestamp):
        self._tickers = tickers
        self._date = date

        self._forecasts = []
        for organism in tqdm.tqdm(population.get_all_organisms(), desc="Forecasts"):
            try:
                forecast = organism.forecast(tickers, date)
            except ForecastError:
                continue
            self._forecasts.append(forecast)

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
