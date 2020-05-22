"""Класс организма и операции с популяцией организмов."""
from typing import Iterable, Tuple, NoReturn, Optional, Dict, Any

import bson
import numpy as np
import pandas as pd
import pymongo
from pymongo.collection import Collection

from poptimizer.config import POptimizerError
from poptimizer.dl import Model, Forecast
from poptimizer.evolve.genotype import Genotype
from poptimizer.store.mongo import DB, MONGO_CLIENT

# Коллекция для хранения моделей
COLLECTION = MONGO_CLIENT[DB]["models"]

# Ключи для хранения описания организма
ID = "_id"
GENOTYPE = "genotype"
WINS = "wins"
MODEL = "model"
LLH = "llh"
DATE = "date"
TICKERS = "tickers"


class OrganismIdError(POptimizerError):
    """Ошибка попытки загрузить организм с отсутствующим в базе ID."""


class ForecastError(OrganismIdError):
    """Отсутствующий прогноз."""


class Organism:
    """Хранящийся в MongoDB организм.

    Загружается по id, создается из описания генотипа или с нуля с генотипом по умолчанию.
    Умеет рассчитывать качество организма для проведения естественного отбора, умирать, размножаться и
    отображать количество пройденных оценок качества.
    """

    def __init__(
        self,
        *,
        _id: Optional[bson.ObjectId] = None,
        genotype: Optional[Genotype] = None,
        collection: Collection = None,
    ):
        collection = collection or COLLECTION
        self.collection = collection

        if _id is None:
            _id = bson.ObjectId()
            organism = {ID: _id, GENOTYPE: genotype}
            collection.insert_one(organism)

        organism = collection.find_one({ID: _id})
        if organism is None:
            raise OrganismIdError(f"В популяции нет организма с ID: {_id}")
        organism[GENOTYPE] = Genotype(organism[GENOTYPE])
        self._data = organism

    def __str__(self) -> str:
        return str(self._data[GENOTYPE])

    @property
    def id(self) -> bson.ObjectId:
        """ID организма."""
        return self._data[ID]

    @property
    def genotype(self) -> Genotype:
        """Генотип организма."""
        return self._data[GENOTYPE]

    def die(self) -> NoReturn:
        """Организм удаляется из популяции."""
        self.collection.delete_one({ID: self._data[ID]})

    def _update(self, update: Dict[str, Any]) -> NoReturn:
        """Обновление данных в MongoDB и внутреннего состояния организма."""
        self._data.update(update)
        self.collection.update_one({ID: self._data[ID]}, {"$set": update})

    @property
    def wins(self) -> int:
        """Количество побед."""
        return self._data.get(WINS, 0)

    def evaluate_fitness(self, tickers: Tuple[str, ...], end: pd.Timestamp) -> float:
        """Вычисляет качество организма.

        Если осуществлялась оценка для указанных тикеров и даты - используется сохраненное значение. Если
        существует натренированная модель для указанных тикеров - осуществляется оценка без тренировки.
        В ином случае тренируется и оценивается с нуля.
        """
        tickers = list(tickers)
        data = self._data
        if data.get(DATE) == end and data.get(TICKERS) == tickers:
            update = {WINS: self.wins + 1}
            self._update(update)
            return data[LLH]

        pickled_model = data.get(MODEL)
        if data.get(TICKERS) != tickers:
            pickled_model = None

        model = Model(
            tuple(tickers), end, self.genotype.get_phenotype(), pickled_model
        )
        llh = model.llh

        update = {
            WINS: self.wins + 1,
            LLH: llh,
            MODEL: bytes(model),
            DATE: end,
            TICKERS: tickers,
        }
        self._update(update)

        return llh

    def make_child(self) -> "Organism":
        """Создает новый организм с помощью дифференциальной мутации."""
        genotypes = [organism.genotype for organism in _sample_organism(3)]
        child_genotype = self.genotype.make_child(*genotypes)
        return Organism(genotype=child_genotype)

    def forecast(self, tickers: Tuple[str, ...], end: pd.Timestamp) -> Forecast:
        """Выдает прогноз для текущего организма.

        При наличие натренированной модели, которая составлена на предыдущей статистике и для таких же
        тикеров, будет использованы сохраненные веса сети, или выбрасывается исключение.
        """
        if (
                (pickled_model := self._data.get(MODEL)) is None
                or tickers != tuple(self._data[TICKERS])
        ):
            raise ForecastError

        model = Model(tickers, end, self.genotype.get_phenotype(), pickled_model)
        return model.forecast()


def _sample_organism(num: int, collection: Collection = None) -> Iterable[Organism]:
    """Выбирает несколько случайных организмов.

    Необходимо для реализации размножения и отбора.
    """
    collection = collection or COLLECTION
    pipeline = [{"$sample": {"size": num}}, {"$project": {"_id": True}}]
    organisms = collection.aggregate(pipeline)
    yield from (Organism(**organism) for organism in organisms)


def count(collection: Collection = None) -> int:
    """Количество организмов в популяции."""
    collection = collection or COLLECTION
    return collection.count_documents({})


def create_new_organism(collection: Collection = None) -> Organism:
    """Создает новый организм с пустым генотипом."""
    collection = collection or COLLECTION
    return Organism(collection=collection)


def get_random_organism(collection: Collection = None) -> Organism:
    """Получить случайный организм из популяции."""
    collection = collection or COLLECTION
    organism, *_ = tuple(_sample_organism(1, collection))
    return organism


def get_all_organisms(collection=None) -> Iterable[Organism]:
    """Получить все имеющиеся организмы."""
    collection = collection or COLLECTION
    id_dicts = collection.find(
        filter={}, projection=["_id"], sort=[(DATE, pymongo.ASCENDING)]
    )
    for id_dict in id_dicts:
        yield Organism(**id_dict)


def print_stat(collection=None) -> NoReturn:
    """Статистика - минимальное и максимальное значение коэффициента Шарпа."""
    collection = collection or COLLECTION
    db_find = collection.find
    cursor = db_find(
        filter={LLH: {"$exists": True}}, projection=[LLH]
    )
    llhs = map(lambda x: x[LLH], cursor)
    llhs = tuple(llhs)
    if llhs:
        quantiles = np.quantile(tuple(llhs), [0.0, 0.5, 1.0])
        quantiles = map(lambda x: f"{x:.4f}", quantiles)
        quantiles = tuple(quantiles)
    else:
        quantiles = ["-"] * 3

    print(f"LLH - ({', '.join(tuple(quantiles))})")

    params = {
        "filter": {WINS: {"$exists": True}},
        "projection": [WINS],
        "sort": [(WINS, pymongo.DESCENDING)],
        "limit": 1,
    }
    wins = list(db_find(**params))
    max_wins = None
    if wins:
        max_wins, *_ = wins
        max_wins = max_wins[WINS]
    print(f"Максимум побед - {max_wins}")
