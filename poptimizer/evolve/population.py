"""Класс организма и операции с популяцией организмов."""
import time
from typing import Iterable, Optional

import bson
import numpy as np
import pandas as pd
import pymongo

from poptimizer.config import POptimizerError
from poptimizer.dl import Forecast, Model
from poptimizer.evolve import store
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
    ) -> None:
        """Загружает организм из базы данных."""
        self._doc = store.Doc(id_=_id, genotype=genotype)

    def __str__(self) -> str:
        """Текстовое представление генотипа организма."""
        return str(self._doc.genotype)

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
        return self._doc.timer

    @property
    def wins(self) -> int:
        """Количество побед."""
        return self._doc.wins

    @property
    def llh(self) -> float:
        """LLH OOS."""
        return self._doc.llh

    def evaluate_fitness(self, tickers: tuple[str, ...], end: pd.Timestamp) -> float:
        """Вычисляет качество организма.

        Если осуществлялась оценка для указанных тикеров и даты - используется сохраненное значение. Если
        существует натренированная модель для указанных тикеров - осуществляется оценка без тренировки.
        В ином случае тренируется и оценивается с нуля.
        """
        tickers = list(tickers)
        doc = self._doc
        doc.wins += 1

        timer = time.monotonic_ns()
        model = Model(tuple(tickers), end, self.genotype.get_phenotype())
        llh = model.llh
        timer = time.monotonic_ns() - timer

        doc.llh = llh
        doc.model = bytes(model)
        doc.date = end
        doc.tickers = tickers

        doc.timer = timer

        doc.save()
        return llh

    def find_weaker(self) -> "Organism":
        """Находит организм с наименьшим llh.

        Ищет самых медленных среди более старых и более слабых.
        Если более старых и слабых нет, то ищет более слабых.
        Может найти самого себя.

        Таким образом, пока не пройден один цикл размножения с новыми данными эволюционный процесс
        старается истреблять медленные организмы. Если за грубо сутки удается перетренировать все
        организмы, то можно искать самые хорошие, не обращая внимание на скорость.
        """
        doc = self._doc
        collection = store.get_collection()

        filter_ = {"llh": {"$lt": doc.llh}, "date": {"$lt": doc.date}, "timer": {"$gt": doc.timer}}
        id_dict = collection.find_one(
            filter=filter_,
            projection=["_id"],
            sort=[("timer", pymongo.DESCENDING)],
        )
        if id_dict is not None:
            org = Organism(**id_dict)
            return org

        filter_ = {}
        id_dict = collection.find_one(
            filter=filter_,
            projection=["_id"],
            sort=[("llh", pymongo.ASCENDING)],
        )
        return Organism(**id_dict)

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
    """Получить лучший из популяции."""
    collection = store.get_collection()
    organism = collection.find_one(
        filter={},
        projection=["_id"],
        sort=[
            ("date", pymongo.ASCENDING),
            ("llh", pymongo.DESCENDING),
        ],
    )
    return Organism(**organism)


def get_all_organisms() -> Iterable[Organism]:
    """Получить все имеющиеся организмы."""
    collection = store.get_collection()
    id_dicts = collection.find(
        filter={},
        projection=["_id"],
        sort=[("date", pymongo.ASCENDING), ("llh", pymongo.DESCENDING)],
    )
    for id_dict in id_dicts:
        try:
            yield Organism(**id_dict)
        except store.IdError:
            pass


def print_stat() -> None:
    """Статистика — минимальное и максимальное значение коэффициента Шарпа."""
    _print_llh_stats()
    _print_wins_stats()


def _print_llh_stats() -> None:
    """Статистика по минимуму, медиане и максимуму llh."""
    collection = store.get_collection()
    db_find = collection.find
    cursor = db_find(filter={"llh": {"$exists": True}}, projection=["llh"])
    llhs = map(lambda doc: doc["llh"], cursor)
    llhs = tuple(llhs)
    if llhs:
        quantiles = np.quantile(tuple(llhs), [0, 0.5, 1.0])
        quantiles = map(lambda quantile: f"{quantile:.4f}", quantiles)
        quantiles = tuple(quantiles)
    else:
        quantiles = ["-" for _ in range(3)]
    print(f"Excess return - ({', '.join(tuple(quantiles))})")


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
    print(f"Максимум побед - {max_wins}")
