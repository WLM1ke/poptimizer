"""Класс организма и операции с популяцией организмов."""
import time
from typing import Iterable, Tuple, NoReturn, Optional

import bson
import numpy as np
import pandas as pd
import pymongo

from poptimizer.config import POptimizerError
from poptimizer.dl import Model, Forecast
from poptimizer.evolve import store
from poptimizer.evolve.chromosomes.chromosome import MUTATION_FACTOR
from poptimizer.evolve.genotype import Genotype


class ForecastError(POptimizerError):
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
    ):
        self._data = store.Doc(id_=_id, genotype=genotype)

    def __str__(self) -> str:
        return str(self._data.genotype)

    @property
    def id(self) -> bson.ObjectId:
        """ID организма."""
        return self._data.id

    @property
    def genotype(self) -> Genotype:
        """Генотип организма."""
        return self._data.genotype

    @property
    def timer(self) -> float:
        """Генотип организма."""
        return self._data.timer

    @property
    def wins(self) -> int:
        """Количество побед."""
        return self._data.wins

    def evaluate_fitness(self, tickers: Tuple[str, ...], end: pd.Timestamp) -> float:
        """Вычисляет качество организма.

        Если осуществлялась оценка для указанных тикеров и даты - используется сохраненное значение. Если
        существует натренированная модель для указанных тикеров - осуществляется оценка без тренировки.
        В ином случае тренируется и оценивается с нуля.
        """
        tickers = list(tickers)
        data = self._data
        data.wins += 1

        if data.date == end and data.tickers == tickers:
            data.save()
            return data.llh

        pickled_model = data.model
        if data.tickers != tickers:
            pickled_model = None

        timer = time.monotonic_ns()
        model = Model(tuple(tickers), end, self.genotype.get_phenotype(), pickled_model)
        llh = model.llh
        timer = time.monotonic_ns() - timer

        data.llh = llh
        data.model = bytes(model)
        data.date = end
        data.tickers = tickers

        if pickled_model is None:
            data.timer = timer

        data.save()
        return llh

    def find_weaker(self) -> "Organism":
        """Находит организм с наименьшим llh.

        В оборе участвуют только организмы с таким же набором тикеров и датой обновления. Может найти
        самого себя.
        """
        data = self._data
        collection = store.get_collection()

        filter_ = dict(timer={"$gte": data.timer}, tickers=data.tickers, date=data.date)
        id_dict = collection.find_one(
            filter=filter_,
            projection=["_id"],
            sort=[("llh", pymongo.ASCENDING)],
        )
        org = Organism(**id_dict)
        if self.id != org.id:
            return org

        filter_ = dict(tickers=data.tickers, date=data.date)
        id_dict = collection.find_one(
            filter=filter_,
            projection=["_id"],
            sort=[("llh", pymongo.ASCENDING)],
        )
        return Organism(**id_dict)

    def die(self) -> NoReturn:
        """Организм удаляется из популяции."""
        self._data.delete()

    def make_child(self, factor: float = MUTATION_FACTOR) -> "Organism":
        """Создает новый организм с помощью дифференциальной мутации."""
        genotypes = [organism.genotype for organism in _sample_organism(3)]
        child_genotype = self.genotype.make_child(*genotypes, factor)
        return Organism(genotype=child_genotype)

    def forecast(self, tickers: Tuple[str, ...], end: pd.Timestamp) -> Forecast:
        """Выдает прогноз для текущего организма.

        При наличие натренированной модели, которая составлена на предыдущей статистике и для таких же
        тикеров, будет использованы сохраненные веса сети, или выбрасывается исключение.
        """
        data = self._data
        if (pickled_model := data.model) is None or tickers != tuple(data.tickers):
            raise ForecastError

        model = Model(tickers, end, self.genotype.get_phenotype(), pickled_model)
        forecast = model.forecast()
        if np.any(np.isnan(forecast.cov)):
            self.die()
            raise ForecastError
        return forecast

    def save(self):
        """Сохраняет все изменения в организме."""
        self._data.save()


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


def get_all_organisms() -> Iterable[Organism]:
    """Получить все имеющиеся организмы."""
    collection = store.get_collection()
    id_dicts = collection.find(
        filter={}, projection=["_id"], sort=[("date", pymongo.ASCENDING), ("llh", pymongo.DESCENDING)]
    )
    for id_dict in id_dicts:
        try:
            yield Organism(**id_dict)
        except store.IdError:
            pass


def print_stat() -> NoReturn:
    """Статистика - минимальное и максимальное значение коэффициента Шарпа."""
    _print_llh_stats()
    _print_wins_stats()


def _print_llh_stats() -> NoReturn:
    """Статистика по минимуму, медиане и максимуму llh."""
    collection = store.get_collection()
    db_find = collection.find
    cursor = db_find(filter=dict(llh={"$exists": True}), projection=["llh"])
    llhs = map(lambda x: x["llh"], cursor)
    llhs = tuple(llhs)
    if llhs:
        quantiles = np.quantile(tuple(llhs), [0.0, 0.5, 1.0])
        quantiles = map(lambda x: f"{x:.4f}", quantiles)
        quantiles = tuple(quantiles)
    else:
        quantiles = ["-"] * 3
    print(f"LLH - ({', '.join(tuple(quantiles))})")


def _print_wins_stats() -> NoReturn:
    """Статистика по максимуму побед."""
    collection = store.get_collection()
    db_find = collection.find
    params = {
        "filter": dict(wins={"$exists": True}),
        "projection": ["wins"],
        "sort": [("wins", pymongo.DESCENDING)],
        "limit": 1,
    }
    wins = list(db_find(**params))
    max_wins = None
    if wins:
        max_wins, *_ = wins
        max_wins = max_wins["wins"]
    print(f"Максимум побед - {max_wins}")
