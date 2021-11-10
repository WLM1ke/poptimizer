"""Формирует прогноз по всем моделям в популяции."""
from collections.abc import Iterable
from typing import Iterator, Optional

import pandas as pd
import tqdm

from poptimizer import config
from poptimizer.dl import Forecast
from poptimizer.evolve import population
from poptimizer.store import database

# База для хранений кеша прогноза и ключ с документа с метаинформацией о прогнозах
FORECAST = "forecasts"
INDEX = "index"


class Forecasts(Iterable):
    """Прогнозы доходностей и ковариационных матриц для DL-моделей."""

    def __init__(
        self,
        tickers: tuple[str, ...],
        date: pd.Timestamp,
        forecasts: Optional[list[Forecast]] = None,
    ):
        """Создает набор прогнозом длинной не более MIN_POPULATION."""
        self._tickers = tickers
        self._date = date

        self._forecasts = forecasts or _prepare_forecasts(tickers, date)
        if not self._forecasts:
            raise population.ForecastError("Отсутствуют прогнозы - необходимо обучить модели")

    def __iter__(self) -> Iterator[Forecast]:
        """Возвращает отдельные прогнозы."""
        yield from self._forecasts

    def __len__(self) -> int:
        """Количество прогнозов."""
        return len(self._forecasts)

    @property
    def tickers(self) -> tuple[str, ...]:
        """Для каких тикеров составлен прогноз."""
        return self._tickers

    @property
    def date(self) -> pd.Timestamp:
        """На какую дату составлен прогноз."""
        return self._date


def _prepare_forecasts(
    tickers: tuple[str, ...],
    date: pd.Timestamp,
    max_count: int = config.TARGET_POPULATION,
) -> list[Forecast]:
    forecasts = []
    for organism in tqdm.tqdm(population.get_oldest(), desc="Forecasts"):
        try:
            forecast = organism.forecast(tickers, date)
        except (population.ForecastError, AttributeError):
            continue

        forecasts.append(forecast)

        if len(forecasts) == max_count:
            break

    return forecasts


class Cache:
    """Создает кэш прогнозов и обновляет его по необходимости."""

    def __init__(
        self,
        tickers: tuple[str, ...],
        date: pd.Timestamp,
        label: str = FORECAST,
    ):
        """Подключается к базе и загружает индекс кэша."""
        self._tickers = tickers
        self._date = date
        self._store = database.MongoDB(collection=label)
        self._index = self._prepare_index(date, tickers)

    def __call__(self) -> Forecasts:
        """Возвращает закешированное значение.

        При его отсутствии вычисляет его и сохраняет в кэш.
        """
        if self._index is not None:
            return self._load_cache()

        return self._create_cache()

    def _prepare_index(self, date, tickers) -> Optional[dict]:
        index = self._store[INDEX]

        if index is not None:
            if index["date"] != date or index["tickers"] != list(tickers):
                self._store.drop()
                index = None

        return index

    def _load_cache(self) -> Forecasts:
        forecasts = [self._store[num] for num in range(self._index["count"])]

        return Forecasts(self._tickers, self._date, forecasts)

    def _create_cache(self) -> Forecasts:
        forecasts = Forecasts(self._tickers, self._date)
        for num, forecast in enumerate(forecasts):
            self._store[num] = forecast

        index = {
            "tickers": self._tickers,
            "date": self._date,
            "count": len(forecasts),
        }
        self._store[INDEX] = index

        return forecasts


def get_forecasts(tickers: tuple[str, ...], date: pd.Timestamp) -> Forecasts:
    """Создает или загружает закешированный прогноз для набора тикеров на указанную дату.

    :param tickers:
        Тикеры, для которых необходимо составить прогноз.
    :param date:
        Дата, на которую нужен прогноз.
    :return:
        Прогнозная доходность, ковариация и дополнительная информация.
    """
    cache = Cache(tickers, date)

    return cache()
