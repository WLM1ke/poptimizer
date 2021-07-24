"""Класс организма и операции с популяцией организмов."""
import contextlib
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


class ForecastError(config.POptimizerError):
    """Отсутствующий прогноз."""


class Organism:
    """Организм и основные операции с ним.

    Умеет рассчитывать качество организма для проведения естественного отбора, умирать, размножаться и
    отображать количество пройденных оценок качества.
    """

    def __init__(
        self,
        *,
        _id: Optional[bson.ObjectId] = None,
        genotype: Optional[Genotype] = None,
    ) -> None:
        """Загружает организм из базы данных."""
        self._doc = store.Doc(id_=_id, genotype=genotype)
        # TODO: временно — убрать после преобразования всех значений
        if isinstance(self._doc.llh, float):
            self._doc.llh = [self._doc.llh + np.log(config.FORECAST_DAYS) / 2]

    def __str__(self) -> str:
        """Текстовое представление генотипа организма."""
        llh_block = -np.inf
        if self.scores > 0:
            llh_all = [f"{llh:.4f}" for llh in self.llh]
            llh_all = ", ".join(llh_all)

            llh = np.array(self.llh).mean()

            llh_block = f"{llh:0.4f}: {llh_all}"

        seconds = self.timer

        blocks = [
            f"LLH — {llh_block}",
            f"IR — {self.ir:0.4f}",
            f"Timer — {seconds}",
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
    def timer(self) -> float:
        """Генотип организма."""
        return self._doc.timer // 10 ** 9

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
        При последующих вызовах в течение дня происходит обучение с нуля.
        """
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
        parent, *_ = [organism.genotype for organism in _sample_organism(1)]
        child_genotype = self.genotype.make_child(parent, scale)
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


def _sample_organism(num: int) -> Iterable[Organism]:
    """Выбирает несколько случайных организмов.

    Необходимо для реализации размножения и отбора.
    """
    collection = store.get_collection()
    pipeline = [{"$sample": {"size": num}}, {"$project": {"_id": True}}]
    organisms = collection.aggregate(pipeline)
    yield from (Organism(**organism) for organism in organisms)


def count() -> int:
    """Количество организмов в популяции."""
    collection = store.get_collection()
    return collection.count_documents({})


def create_new_organism() -> Organism:
    """Создает новый организм с пустым генотипом и сохраняет его в базе данных."""
    org = Organism()
    org.save()
    return org


def get_random_organism() -> Organism:
    """Получить случайный организм из популяции."""
    organism, *_ = tuple(_sample_organism(1))
    return organism


def get_parent() -> Organism:
    """Родитель отбирается по максимуму последнего llh среди давно не тренировавшихся."""
    collection = store.get_collection()
    pipeline = [
        {
            "$project": {
                "date": True,
                "llh": {"$avg": "$llh"},
                "llh_last": {"$arrayElemAt": ["$llh", 0]},
                "ir": True,
                "total": {"$multiply": ["$timer", "$wins"]},
            },
        },
        {"$sort": {"date": pymongo.ASCENDING, "llh_last": pymongo.DESCENDING}},
        {"$limit": 1},
        {"$project": {"_id": True}},
    ]
    doc = next(collection.aggregate(pipeline))

    return Organism(**doc)


def get_prey() -> Organism:
    """Жертва — самый слабый по LLH среди давно не оценивавшихся."""
    collection = store.get_collection()
    pipeline = [
        {"$project": {"date": True, "llh": {"$avg": "$llh"}}},
        {"$sort": {"date": pymongo.ASCENDING, "llh": pymongo.ASCENDING}},
        {"$limit": 1},
        {"$project": {"_id": True}},
    ]
    doc = next(collection.aggregate(pipeline))

    return Organism(**doc)


def get_all_organisms() -> Iterable[Organism]:
    """Получить все имеющиеся организмы."""
    collection = store.get_collection()
    id_dicts = collection.find(
        filter={},
        projection=["_id"],
        sort=[("date", pymongo.ASCENDING), ("llh", pymongo.DESCENDING)],
    )
    for id_dict in id_dicts:
        with contextlib.suppress(store.IdError):
            yield Organism(**id_dict)


def print_stat() -> None:
    """Статистика — минимальное и максимальное значение коэффициента Шарпа."""
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

    print(f"Максимум оценок - {max_wins}")  # noqa: WPS421
