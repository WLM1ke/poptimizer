"""Класс организма и операции с популяцией организмов."""
import contextlib
import datetime
import time
from typing import Iterable, Optional

import bson
import numpy as np
import pandas as pd
import pymongo

from poptimizer import config
from poptimizer.dl import Forecast, Model
from poptimizer.evolve import store
from poptimizer.evolve.genotype import Genotype

# Преобразование времени в секунды
TIME_TO_SEC = 10 ** 9


class ReevaluationError(config.POptimizerError):
    """Попытка сделать вторую оценку для заданной даты."""


class ForecastError(config.POptimizerError):
    """Отсутствующий прогноз."""


class Organism:
    """Организм и основные операции с ним.

    Умеет рассчитывать качество организма для проведения естественного отбора, умирать, размножаться.
    """

    def __init__(
        self,
        *,
        _id: Optional[bson.ObjectId] = None,
        genotype: Optional[Genotype] = None,
    ) -> None:
        """Загружает организм из базы данных."""
        self._doc = store.Doc(id_=_id, genotype=genotype)

    def __str__(self) -> str:
        """Текстовое представление генотипа организма."""
        llh_block = -np.inf
        if self.scores > 0:
            llh_all = [f"{llh:.4f}" for llh in self.llh]
            llh_all = ", ".join(llh_all)

            llh = np.array(self.llh).mean()

            llh_block = f"{llh:0.4f}: {llh_all}"

        timer = datetime.timedelta(seconds=self.timer // TIME_TO_SEC)

        blocks = [
            f"LLH — {llh_block}",
            f"IR — {self.ir:0.4f}",
            f"Timer — {timer}",
            str(self._doc.genotype),
        ]

        return "\n".join(blocks)

    @property
    def id(self) -> bson.ObjectId:
        """ID организма."""
        return self._doc.id

    @property
    def genotype(self) -> Genotype:
        """Генотип организма."""
        return self._doc.genotype

    @property
    def date(self) -> pd.Timestamp:
        """Дата последнего расчета."""
        return self._doc.date

    @property
    def timer(self) -> float:
        """Генотип организма."""
        return self._doc.timer

    @property
    def scores(self) -> int:
        """Количество оценок LLH."""
        return len(self.llh)

    @property
    def llh(self) -> list[float]:
        """List of LLH OOS."""
        return self._doc.llh

    @property
    def ir(self) -> float:
        """Information ratio."""
        return self._doc.ir

    def evaluate_fitness(self, tickers: tuple[str, ...], end: pd.Timestamp) -> list[float]:
        """Вычисляет качество организма.

        В первый вызов для нового дня используется метрика существующей натренированной модели.
        При последующих вызовах в течение дня выбрасывается ошибка.
        """
        if end == self.date:
            raise ReevaluationError

        tickers = list(tickers)
        doc = self._doc

        pickled_model = None
        if doc.date is not None and doc.date < end and tickers == doc.tickers:
            pickled_model = doc.model

        timer = time.monotonic_ns()
        model = Model(tuple(tickers), end, self.genotype.get_phenotype(), pickled_model)
        llh, ir = model.quality_metrics

        if pickled_model is None:
            doc.timer = time.monotonic_ns() - timer

        doc.llh = [llh] + doc.llh
        doc.wins = len(doc.llh)
        doc.ir = ir

        doc.model = bytes(model)

        doc.date = end
        doc.tickers = tickers

        doc.save()

        return self.llh

    def die(self) -> None:
        """Организм удаляется из популяции."""
        self._doc.delete()

    def make_child(self, scale: float) -> "Organism":
        """Создает новый организм с помощью дифференциальной мутации."""
        parent1, parent2 = _get_parents()
        child_genotype = self.genotype.make_child(parent1.genotype, parent2.genotype, scale)

        return Organism(genotype=child_genotype)

    def forecast(self, tickers: tuple[str, ...], end: pd.Timestamp) -> Forecast:
        """Выдает прогноз для текущего организма.

        При наличии натренированной модели, которая составлена на предыдущей статистике и для таких же
        тикеров, будет использованы сохраненные веса сети, или выбрасывается исключение.
        """
        doc = self._doc
        if (pickled_model := doc.model) is None or tickers != tuple(doc.tickers):
            raise ForecastError

        model = Model(tickers, end, self.genotype.get_phenotype(), pickled_model)
        forecast = model.forecast()
        if np.any(np.isnan(forecast.cov)):
            self.die()
            raise ForecastError
        return forecast

    def save(self) -> None:
        """Сохраняет все изменения в организме."""
        self._doc.save()


def count() -> int:
    """Количество организмов в популяции."""
    collection = store.get_collection()

    return collection.count_documents({})


def create_new_organism() -> Organism:
    """Создает новый организм с пустым генотипом и сохраняет его в базе данных."""
    org = Organism()
    org.save()

    return org


def get_next_one(date: Optional[pd.Timestamp]) -> Optional[Organism]:
    """Последовательно выдает организмы с датой не равной данной и None при отсутствии.

    В первую очередь выдаются организмы с минимальным количеством оценок.
    """
    collection = store.get_collection()
    doc = collection.find_one(
        filter={"date": {"$ne": date}},
        sort=[("wins", pymongo.ASCENDING)],
        projection={"_id": True},
        limit=1,
    )

    return doc and Organism(**doc)


def _get_parents() -> tuple[Organism, Organism]:
    """Получить родителей с разным генотипом."""
    collection = store.get_collection()

    pipeline = [
        {"$project": {"_id": True}},
        {"$sample": {"size": 2}},
    ]

    parent1, parent2 = [Organism(**doc) for doc in collection.aggregate(pipeline)]

    if parent1.genotype == parent2.genotype:
        return Organism(), Organism()

    return parent1, parent2


def get_oldest(limit: int = config.MIN_POPULATION) -> Iterable[Organism]:
    """Получить самые старые.

    При одинаковом возрасте сортировать по среднему llh.
    """
    collection = store.get_collection()

    pipeline = [
        {"$project": {"_id": True, "wins": True, "llh": {"$avg": "$llh"}}},
        {"$sort": {"wins": pymongo.DESCENDING, "llh": pymongo.DESCENDING}},
        {"$limit": limit},
        {"$project": {"_id": True}},
    ]

    for id_dict in collection.aggregate(pipeline):
        with contextlib.suppress(store.IdError):
            yield Organism(**id_dict)


def min_max_date() -> tuple[pd.Timestamp, pd.Timestamp]:
    """Минимальная и максимальная дата в популяции."""
    collection = store.get_collection()

    pipeline = [
        {
            "$group": {
                "_id": {},
                "min": {"$min": "$date"},
                "max": {"$max": "$date"},
            },
        },
    ]
    doc = next(collection.aggregate(pipeline), {})

    return (
        pd.Timestamp(doc.get("min")),
        pd.Timestamp(doc.get("max")),
    )


def get_llh(date: pd.Timestamp) -> list:
    """Значения llh, wins и timer для заданной даты отсортированные по убыванию llh."""
    collection = store.get_collection()
    pipeline = [
        {"$match": {"date": {"$eq": date}}},
        {"$project": {"llh": {"$first": "$llh"}, "timer": True, "wins": True}},
        {"$sort": {"llh": pymongo.DESCENDING}},
    ]

    return list(collection.aggregate(pipeline))


def print_stat() -> None:
    """Распечатка сводных статистических данных по популяции."""
    _print_key_stats("llh")
    _print_key_stats("ir")
    _print_wins_stats()


def _print_key_stats(key: str) -> None:
    """Статистика по минимуму, медиане и максимуму llh."""
    collection = store.get_collection()
    db_find = collection.find
    cursor = db_find(filter={key: {"$exists": True}}, projection=[key])

    keys = map(lambda doc: doc[key], cursor)
    keys = map(
        lambda amount: amount if isinstance(amount, float) else np.array(amount).mean(),
        keys,
    )
    keys = filter(
        lambda amount: not np.isnan(amount),
        keys,
    )
    keys = tuple(keys)

    if keys:
        quantiles = np.quantile(keys, [0, 0.5, 1.0])
        quantiles = map(lambda quantile: f"{quantile:.4f}", quantiles)
        quantiles = tuple(quantiles)
    else:
        quantiles = ["-" for _ in range(3)]

    quantiles = ", ".join(tuple(quantiles))

    print(f"{key.upper()} - ({quantiles})")  # noqa: WPS421


def _print_wins_stats() -> None:
    """Статистика по максимуму побед."""
    collection = store.get_collection()
    db_find = collection.find
    request = {
        "filter": {"wins": {"$exists": True}},
        "projection": ["wins"],
        "sort": [("wins", pymongo.DESCENDING)],
        "limit": 1,
    }
    wins = list(db_find(**request))
    max_wins = None
    if wins:
        max_wins, *_ = wins
        max_wins = max_wins["wins"]

    print(f"Организмов - {count()} /", f"Максимум оценок - {max_wins}")  # noqa: WPS421
