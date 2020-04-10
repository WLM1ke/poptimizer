"""Класс организма и операции с популяцией организмов."""
from typing import Iterable, Tuple, NoReturn, Optional, Dict, Any

import bson
import pandas as pd
from pymongo.collection import Collection

from poptimizer.dl.trainer import Trainer
from poptimizer.evolve.genotype import Genotype
from poptimizer.store.mongo import DB, MONGO_CLIENT

# Коллекция для хранения моделей
COLLECTION = MONGO_CLIENT[DB]["models"]

# Ключи для хранения описания организма
ID = "_id"
GENOTYPE = "genotype"
WINS = "wins"
MODEL = "model"
SHARPE = "sharpe"
SHARPE_DATE = "sharpe_date"


class Organism:
    """Хранящийся в MongoDB организм.

    Загружается по id, создается из описания генотипа или с нуля с генотипом по умолчанию.
    Умеет рассчитывать качество организма для проведения естественного отбора, убивать другой
    организм, умирать, размножаться и отображать количество уничтоженных организмов.
    """

    def __init__(
        self,
        _id: Optional[bson.ObjectId] = None,
        genotype: Optional[Genotype] = None,
        collection: Collection = COLLECTION,
    ):
        self.collection = collection

        if _id is None:
            _id = bson.ObjectId()
            organism = {ID: _id, GENOTYPE: genotype}
            collection.insert_one(organism)

        organism = collection.find_one({ID: _id})
        organism[GENOTYPE] = Genotype(organism[GENOTYPE])
        self._data = organism

    def __str__(self) -> str:
        return str(self._data[GENOTYPE])

    def _update(self, update: Dict[str, Any]) -> NoReturn:
        """Обновление данных в MongoDB и внутреннего состояния организма."""
        self._data.update(update)
        self.collection.update_one({ID: self._data[ID]}, {"$set": update})

    @property
    def wins(self) -> int:
        """Количество побед."""
        return self._data.get(WINS, 0)

    def evaluate_fitness(self, tickers: Tuple[str, ...], end: pd.Timestamp) -> float:
        """Вычисляет коэффициент Шарпа."""
        organism = self._data

        if organism.get(SHARPE_DATE) == end:
            return organism[SHARPE]

        trainer = Trainer(tickers, end, organism[GENOTYPE].get_phenotype())
        sharpe = trainer.sharpe
        model = trainer.model

        update = {SHARPE: sharpe, SHARPE_DATE: end, MODEL: model}
        self._update(update)

        return sharpe

    def die(self) -> NoReturn:
        """Организм удаляется из популяции."""
        self.collection.delete_one({ID: self._data[ID]})

    def make_child(self) -> "Organism":
        """Создает новый организм с помощью дифференциальной мутации."""
        genotypes = [organism._data[GENOTYPE] for organism in _sample_organism(3)]
        child_genotype = self._data[GENOTYPE].make_child(*genotypes)
        return Organism(genotype=child_genotype)

    def kill(self, organism: "Organism") -> NoReturn:
        """Убивает другой организм и ведет счет побед."""
        update = {WINS: self.wins + 1}
        self._update(update)
        organism.die()


def _sample_organism(
    num: int, collection: Collection = COLLECTION
) -> Iterable[Organism]:
    """Выбирает несколько случайных организмов.

    Необходимо для реализации размножения и отбора.
    """
    pipeline = [{"$sample": {"size": num}}, {"$project": {"_id": True}}]
    organisms = collection.aggregate(pipeline)
    yield from (Organism(organism[ID]) for organism in organisms)


def count(collection: Collection = COLLECTION) -> int:
    """Количество организмов в популяции."""
    return collection.count_documents({})


def create_new_organism(collection: Collection = COLLECTION) -> Organism:
    """Создает новый организм с пустым генотипом."""
    return Organism(collection=collection)


def get_random_organism(collection: Collection = COLLECTION) -> Organism:
    """Получить случайный организм из популяции."""
    organism, *_ = tuple(_sample_organism(1, collection))
    return organism


def get_all_organisms(collection=COLLECTION) -> Iterable[Organism]:
    """Получить все имеющиеся организмы."""
    id_dicts = collection.find(filter={}, projection=["_id"], sort=[(SHARPE, 1)])
    for id_dict in id_dicts:
        yield Organism(**id_dict)


def print_stat(collection=COLLECTION) -> NoReturn:
    """Статистика - минимальное и максимальное значение коэффициента Шарпа."""
    db_find = collection.find

    sort_type = (1, -1)
    params = {"filter": {SHARPE: {"$exists": True}}, "projection": [SHARPE], "limit": 1}
    cursors = (db_find(sort=[(SHARPE, up_down)], **params) for up_down in sort_type)
    sharpes = [tuple(cursor) for cursor in cursors]
    sharpes = [f"{sharpe[0][SHARPE]:.4f}" if sharpe else "-" for sharpe in sharpes]
    print(f"Коэффициент Шарпа - ({', '.join(sharpes)})")

    params = {
        "filter": {WINS: {"$exists": True}},
        "projection": [WINS],
        "sort": [(WINS, -1)],
        "limit": 1,
    }
    wins = list(db_find(**params))
    print(wins)
    max_wins = None
    if wins:
        max_wins, *_ = wins
        max_wins = max_wins[WINS]
    print(f"Максимум побед - {max_wins}")
