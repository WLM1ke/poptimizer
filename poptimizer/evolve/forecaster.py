"""Формирует прогноз по всем моделям в популяции."""
from collections.abc import Iterable
from typing import Tuple, Iterator

import pandas as pd
import tqdm
from pymongo.collection import Collection

from poptimizer import store
from poptimizer.dl import Forecast
from poptimizer.evolve import population
from poptimizer.evolve.population import ForecastError

# Ключ для хранений кеша прогноза
FORECAST = "dl"


class Forecasts(Iterable):
    """Прогнозы доходностей и ковариационных матриц для DL-моделей."""

    def __init__(
        self,
        tickers: Tuple[str, ...],
        date: pd.Timestamp,
        collection: Collection = None,
    ):
        self._tickers = tickers
        self._date = date

        self._forecasts = []
        for organism in tqdm.tqdm(
            population.get_all_organisms(collection), desc="Forecasts"
        ):
            try:
                forecast = organism.forecast(tickers, date)
            except ForecastError:
                continue
            self._forecasts.append(forecast)

    def __iter__(self) -> Iterator[Forecast]:
        yield from self._forecasts

    @property
    def tickers(self) -> Tuple[str, ...]:
        """Для каких тикеров составлен прогноз."""
        return self._tickers

    @property
    def date(self) -> pd.Timestamp:
        """На какую дату составлен прогноз."""
        return self._date


def get_forecasts(
    tickers: Tuple[str, ...], date: pd.Timestamp, collection: Collection = None
) -> Forecasts:
    """Создает или загружает закешированный прогноз для набора тикеров на указанную дату.

    :param tickers:
        Тикеры, для которых необходимо составить прогноз.
    :param date:
        Дата, на которую нужен прогноз.
    :param collection:
        Коллекция с организмами - нужно для тестирования.
    :return:
        Прогнозная доходность, ковариация и дополнительная информация.
    """
    mongodb = store.MongoDB(db=collection.database.name)
    forecasts_cache = mongodb[FORECAST]
    if (
        forecasts_cache is not None
        and forecasts_cache.date == date
        and forecasts_cache.tickers == tickers
    ):
        return forecasts_cache
    forecasts = Forecasts(tickers, date, collection)
    mongodb[FORECAST] = forecasts
    return forecasts
