"""Класс организма и операции с популяцией организмов."""
import contextlib
import datetime
import logging
import random
import time
from typing import Iterable, Iterator, Optional

import bson
import numpy as np
import pandas as pd
import pymongo

from poptimizer import config
from poptimizer.dl import Forecast, Model
from poptimizer.evolve import store
from poptimizer.evolve.genotype import Genotype

# Преобразование времени в секунды
TIME_TO_SEC = 10**9

LOGGER = logging.getLogger()


class ReevaluationError(config.POptimizerError):
    """Попытка сделать вторую оценку для заданной даты."""


class ForecastError(config.POptimizerError):
    """Отсутствующий прогноз."""


class Organism:  # noqa: WPS214
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
        llh_block = _format_scores_list(self.llh)
        ir_block = _format_scores_list(self.ir)

        timer = datetime.timedelta(seconds=self.timer // TIME_TO_SEC)

        blocks = [
            f"LLH — {llh_block}",
            f"RET — {ir_block}",
            f"Timer — {timer} / Scores - {self.scores}",
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
        return self._doc.wins

    @property
    def llh(self) -> list[float]:
        """List of LLH OOS."""
        return self._doc.llh

    @property
    def ir(self) -> list[float]:
        """List of information ratios."""
        return self._doc.ir

    @property
    def tickers(self) -> list[str]:
        return self._doc.tickers

    @property
    def upper_bound(self) -> float:
        """Верхняя граница доверительного интервала."""
        return self._doc.ub

    @upper_bound.setter
    def upper_bound(self, ub: float) -> None:
        """Изменение значения верхней границы доверительного интервала."""
        self._doc.ub = ub
        self._doc.save()

    def retrain(self, tickers: tuple[str, ...], end: pd.Timestamp):
        """Переобучает модель."""
        timer = time.monotonic_ns()
        model = Model(tuple(tickers), end, self.genotype.get_phenotype(), None)
        model.quality_metrics
        self._doc.model = bytes(model)
        self._doc.tickers = list(tickers)
        self._doc.timer = time.monotonic_ns() - timer

    def evaluate_fitness(self, tickers: tuple[str, ...], end: pd.Timestamp) -> list[float]:
        """Вычисляет качество организма."""
        doc = self._doc
        tickers = list(tickers)

        if end == self.date or doc.model is None or tickers != doc.tickers:
            raise ReevaluationError

        model = Model(tuple(tickers), end, self.genotype.get_phenotype(), doc.model)
        llh, ir = model.quality_metrics

        if self.date is None or end > self.date:
            doc.llh = [llh] + doc.llh
            doc.ir = [ir] + doc.ir
            doc.date = end
        else:
            doc.llh = doc.llh + [llh]
            doc.ir = doc.ir + [ir]

        doc.wins = len(doc.llh)

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
        if np.any(np.isnan(forecast.cov)) or np.any(np.isinf(forecast.cov)):
            self.die()
            raise ForecastError

        return forecast

    def save(self) -> None:
        """Сохраняет все изменения в организме."""
        self._doc.save()


def _format_scores_list(scores: list[float]) -> str:
    block = "-"
    if scores:
        scores_all = [f"{score: .4f}" for score in scores]
        scores_all = ", ".join(scores_all)

        score = np.median(np.array(scores))

        block = f"{score: .4f}: {scores_all}"

    return block


def count() -> int:
    """Количество организмов в популяции."""
    collection = store.get_collection()

    return collection.count_documents({})


def create_new_organism() -> Organism:
    """Создает новый организм с пустым генотипом и сохраняет его в базе данных."""
    org = Organism()
    org.save()

    return org


def _get_parents() -> tuple[Organism, Organism]:
    """Получить родителей.

    Если популяция меньше 2 организмов, то используются два организма с базовыми случайными генотипами.
    """
    collection = store.get_collection()

    pipeline = [
        {"$project": {"_id": True}},
        {"$sample": {"size": 2}},
    ]

    parents = tuple(Organism(**doc) for doc in collection.aggregate(pipeline))

    if len(parents) == 2:
        return parents[0], parents[1]

    return Organism(), Organism()


def _aggregate_oldest(limit: int, first_steps: Optional[list[dict]] = None):
    """Берет первые документы по возрастанию id.

    При наличии добавляет первый шаг агрегации.
    """
    pipeline = [
        {"$project": {"ir": True, "llh": True, "date": True, "timer": True}},
        {"$sort": {"_id": pymongo.ASCENDING}},
        {"$limit": limit},
    ]
    if first_steps:
        pipeline = first_steps + pipeline

    return store.get_collection().aggregate(pipeline)


def get_next_one() -> Optional[Organism]:
    """Выдает организмы по возрастанию даты.

    Второй критерий - или самый мало обученный, или с максимальной верхней границе доверительного интервала.
    """
    selector = random.choice(({"ub": pymongo.DESCENDING}, {"wins": pymongo.ASCENDING}))

    pipeline = [
        {"$project": {"date": True, "ub": True, "wins": True}},
        {"$sort": {"date": pymongo.ASCENDING} | selector},
        {"$limit": 1},
    ]

    doc = next(store.get_collection().aggregate(pipeline))

    return doc and Organism(_id=doc["_id"])


def get_metrics() -> Iterable[dict[str, list[float]]]:
    """Данные о ключевых параметрах популяции."""
    yield from _aggregate_oldest(count(), [{"$match": {"date": {"$exists": True}}}])


def get_all() -> Iterator[Organism]:
    """Получить все организмы."""
    for doc in list(_aggregate_oldest(count())):
        with contextlib.suppress(store.IdError):
            yield Organism(_id=doc["_id"])


def min_max_date() -> tuple[Optional[pd.Timestamp], Optional[pd.Timestamp]]:
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
    if doc.get("max") is None:
        return None, None

    return pd.Timestamp(doc["min"]), pd.Timestamp(doc["max"])


def print_stat() -> None:
    """Распечатка сводных статистических данных по популяции."""
    _print_key_stats("llh")
    _print_key_stats("ir", "RET")


def _print_key_stats(key: str, view: str = None) -> None:
    """Статистика по минимуму, медиане и максимуму llh."""
    collection = store.get_collection()
    db_find = collection.find
    cursor = db_find(filter={key: {"$exists": True}}, projection=[key])

    keys = map(lambda doc: doc[key], cursor)
    keys = map(
        lambda amount: amount if isinstance(amount, float) else np.median(np.array(amount)),
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
    view = view or key.upper()

    LOGGER.info(f"{view} - ({quantiles})")  # noqa: WPS421


def min_scores() -> int:
    collection = store.get_collection()
    db_find = collection.find
    request = {
        "filter": {"wins": {"$exists": True}},
        "projection": ["wins"],
        "sort": [("wins", pymongo.ASCENDING)],
        "limit": 1,
    }

    wins = list(db_find(**request))
    max_wins = 0
    if wins:
        max_wins = wins[0]
        max_wins = max_wins["wins"]

    return max_wins


def max_scores() -> int:
    collection = store.get_collection()
    db_find = collection.find
    request = {
        "filter": {"wins": {"$exists": True}},
        "projection": ["wins"],
        "sort": [("wins", pymongo.DESCENDING)],
        "limit": 1,
    }

    wins = list(db_find(**request))
    max_wins = 0
    if wins:
        max_wins = wins[0]
        max_wins = max_wins["wins"]

    return max_wins
