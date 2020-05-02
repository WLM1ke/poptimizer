from typing import Iterable

import pandas as pd
import pytest

from poptimizer.evolve import population
from poptimizer.evolve.genotype import Genotype
from poptimizer.store.mongo import DB, MONGO_CLIENT

TEST_COLLECTION = MONGO_CLIENT[DB]["Test"]


@pytest.fixture(scope="function", autouse=True)
def test_db(monkeypatch):
    monkeypatch.setattr(population, "COLLECTION", TEST_COLLECTION)
    yield
    TEST_COLLECTION.drop()


def test_create_empty_organism():
    organism = population.Organism()
    assert len(organism._data) == 2
    assert isinstance(organism._data[population.GENOTYPE], Genotype)
    id_ = organism.id

    organism_data = TEST_COLLECTION.find_one({population.ID: id_})
    assert len(organism_data) == 2
    assert organism_data[population.ID] == id_
    assert organism_data[population.GENOTYPE] is None


def test_create_organism_from_genotype_and_reload():
    genotype_data = {"Scheduler": {"max_lr": 7}}
    organism = population.Organism(genotype=Genotype(genotype_data))
    assert len(organism._data) == 2
    assert isinstance(organism._data[population.GENOTYPE], Genotype)
    id_ = organism.id
    genotype = organism._data[population.GENOTYPE]
    assert genotype["Scheduler"]["max_lr"] == 7

    organism_data = TEST_COLLECTION.find_one({population.ID: id_})
    assert len(organism_data) == 2
    assert organism_data[population.ID] == id_
    assert organism_data[population.GENOTYPE] == genotype
    assert organism_data[population.GENOTYPE]["Scheduler"]["max_lr"] == 7

    organism = population.Organism(_id=id_)
    assert len(organism._data) == 2
    assert organism.id == id_
    assert organism._data[population.GENOTYPE] == genotype
    assert organism._data[population.GENOTYPE]["Scheduler"]["max_lr"] == 7


def test_die():
    organism = population.Organism()
    id_ = organism.id
    assert population.Organism(_id=id_).id == id_

    organism.die()

    with pytest.raises(population.OrganismIdError) as error:
        population.Organism(_id=id_)
    assert "В популяции нет организма с ID" in str(error.value)


def test_initial_wins():
    assert population.Organism().wins == 0


class FakeModel:
    COUNTER = 0

    # noinspection PyUnusedLocal
    def __init__(self, tickers, end, phenotype, pickled_model):
        pass

    @property
    def information_ratio(self):
        self.__class__.COUNTER += 1
        return 5

    def __bytes__(self):
        return bytes(6)


def test_evaluate_fitness(monkeypatch):
    monkeypatch.setattr(population, "Model", FakeModel)

    organism = population.Organism()
    id_ = organism.id

    assert FakeModel.COUNTER == 0
    sharpe = organism.evaluate_fitness(("GAZP", "AKRN"), pd.Timestamp("2020-04-12"))

    assert sharpe == 5
    assert FakeModel.COUNTER == 1
    assert organism.wins == 1

    organism_reloaded = population.Organism(_id=id_)

    assert organism_reloaded._data[population.INFORMATION_RATIO] == 5
    assert organism_reloaded._data[population.DATE] == pd.Timestamp("2020-04-12")
    assert organism_reloaded._data[population.TICKERS] == ["GAZP", "AKRN"]
    assert organism_reloaded._data[population.MODEL] == bytes(6)
    assert organism.wins == 1

    assert (
        organism_reloaded.evaluate_fitness(("GAZP", "AKRN"), pd.Timestamp("2020-04-12"))
        == 5
    )
    assert FakeModel.COUNTER == 2
    assert organism_reloaded.wins == 2

    assert (
        organism_reloaded.evaluate_fitness(("GAZP", "LKOH"), pd.Timestamp("2020-04-12"))
        == 5
    )
    assert FakeModel.COUNTER == 3
    assert organism_reloaded.wins == 3

    assert (
        organism_reloaded.evaluate_fitness(("GAZP", "LKOH"), pd.Timestamp("2020-04-13"))
        == 5
    )
    assert FakeModel.COUNTER == 4
    assert organism_reloaded.wins == 4

    assert (
        organism_reloaded.evaluate_fitness(("GAZP", "LKOH"), pd.Timestamp("2020-04-13"))
        == 5
    )
    assert FakeModel.COUNTER == 4
    assert organism_reloaded.wins == 5


def test_make_child():
    organism = population.Organism()
    # Нужно минимум три организма для дифференциальной эволюции
    population.Organism()
    population.Organism()

    assert isinstance(organism.make_child(), population.Organism)


def test_count():
    assert population.count() == 0

    org1 = population.Organism()
    assert population.count() == 1

    org2 = population.Organism()
    assert population.count() == 2

    org1.die()
    assert population.count() == 1

    org2.die()
    assert population.count() == 0


def test_create_new_organism():
    org = population.create_new_organism()
    assert isinstance(org, population.Organism)

    id_ = org.id
    organism_data = TEST_COLLECTION.find_one({population.ID: id_})
    assert len(organism_data) == 2
    assert organism_data[population.ID] == id_
    assert organism_data[population.GENOTYPE] is None


def test_get_random_organism():
    ids = set()
    ids.add(population.Organism().id)
    ids.add(population.Organism().id)
    ids.add(population.Organism().id)

    org = population.get_random_organism()
    assert org.id in ids


def test_get_all_organisms():
    ids = list()
    ids.append(population.Organism().id)
    ids.append(population.Organism().id)
    ids.append(population.Organism().id)
    ids.sort()

    organisms = population.get_all_organisms()
    assert isinstance(organisms, Iterable)

    assert sorted(org.id for org in organisms) == ids
