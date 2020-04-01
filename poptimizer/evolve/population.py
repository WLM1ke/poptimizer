"""Класс организма."""
from typing import Iterable

import bson

from poptimizer.dl.trainer import Trainer
from poptimizer.evolve.genotype import Genotype
from poptimizer.store.mongo import DB, MONGO_CLIENT

# Коллекция для хранения моделей
COLLECTION = MONGO_CLIENT[DB]["models"]

# Ключи для хранения описания организма
ID = "_id"
GENOTYPE = "genotype"
MODEL = "model"
SHARPE = "sharpe"
SHARPE_DATE = "sharpe_date"


class Organism:
    """Организм."""

    def __init__(
        self,
        *,
        _id=None,
        genotype=None,
        model=None,
        sharpe=None,
        sharpe_date=None,
        collection=COLLECTION,
    ):
        self.collection = collection

        self.id = _id or bson.ObjectId()
        self.genotype = Genotype(genotype)
        if _id is None:
            organism = {ID: self.id, GENOTYPE: self.genotype.as_dict}
            self.collection.insert_one(organism)

        self.model = model
        self.sharpe = sharpe
        self.sharpe_date = sharpe_date

    def __str__(self):
        return str(self.genotype)

    def fitness(self, tickers, end):
        """Вычисляет коэффициент Шарпа."""
        if self.sharpe_date == end:
            return self.sharpe

        trainer = Trainer(tickers, end, self.genotype.phenotype, self.model)
        sharpe = trainer.sharpe
        self.sharpe = sharpe
        self.sharpe_date = end
        update = {SHARPE: sharpe, SHARPE_DATE: end}

        if self.model is None:
            self.model = trainer.model
            update[MODEL] = self.model

        self.collection.update_one({ID: self.id}, {"$set": update})
        return sharpe

    def kill(self):
        """Убивает организм."""
        self.collection.delete_one({ID: self.id})

    def make_child(self):
        """Осуществляет одну мутацию и сохраняет полученный генотип в MongoDB."""
        genotypes = [organism.genotype for organism in sample_organism(3)]
        child_genotype = self.genotype.make_child(*genotypes)
        return Organism(genotype=child_genotype)


def sample_organism(num: int, collection=COLLECTION) -> Iterable["Organism"]:
    """Выбирает несколько случайных организмов.

    Необходимо для реализации размножения и отбора.
    """
    organisms = collection.aggregate([{"$sample": {"size": num}}])
    return [Organism(**organism) for organism in organisms]


def count(collection=COLLECTION) -> int:
    """Количество документов в коллекции."""
    return collection.count_documents({})


def print_stat(collection=COLLECTION) -> None:
    """Статистика - минимальное и максимальное значение коэффициента Шарпа."""
    rez = (
        list(collection.find({SHARPE: {"$exists": True}}, sort=[(SHARPE, 1)], limit=1)),
        list(
            collection.find({SHARPE: {"$exists": True}}, sort=[(SHARPE, -1)], limit=1)
        ),
    )
    doc = (None, None)
    if len(rez[0]) > 0:
        doc = tuple(i[SHARPE] for i, *_ in rez)
    print(f"Значения коэффициента Шарпа лежат в интервале {doc}")
