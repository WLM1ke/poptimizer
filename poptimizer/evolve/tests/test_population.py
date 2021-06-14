from typing import Iterable

import pandas as pd
import pytest

from poptimizer.dl import Forecast
from poptimizer.evolve import population, store


@pytest.fixture(scope="module", autouse=True)
def set_test_collection():
    # noinspection PyProtectedMember
    saved_collection = store._COLLECTION
    test_collection = saved_collection.database["test"]
    store._COLLECTION = test_collection

    yield

    store._COLLECTION = saved_collection
    test_collection.drop()


class FakeModel:
    COUNTER = 0

    # noinspection PyUnusedLocal
    def __init__(self, tickers, end, phenotype, pickled_model=None):
        pass

    @property
    def llh(self):
        self.__class__.COUNTER += 1
        return 5

    def __bytes__(self):
        return bytes(6)


@pytest.fixture()
def fake_model(monkeypatch):
    monkeypatch.setattr(population, "Model", FakeModel)
    yield


@pytest.fixture(scope="module", name="organism")
def make_organism():
    test_organism = population.Organism()
    yield test_organism


@pytest.mark.usefixtures("fake_model")
def test_evaluate_fitness(organism):
    assert FakeModel.COUNTER == 0

    fitness = organism.evaluate_fitness(("GAZP", "AKRN"), pd.Timestamp("2020-04-12"))

    assert fitness == 5
    assert FakeModel.COUNTER == 1
    assert organism.wins == 1
    assert organism._doc.date == pd.Timestamp("2020-04-12")
    assert organism._doc.tickers == ["GAZP", "AKRN"]
    assert organism._doc.model == bytes(6)
    assert organism._doc.timer > 0


def test_reload_organism(organism):
    population.Organism(_id=organism.id)

    assert organism._doc.llh == 5
    assert organism._doc.date == pd.Timestamp("2020-04-12")
    assert organism._doc.tickers == ["GAZP", "AKRN"]
    assert organism._doc.model == bytes(6)
    assert organism._doc.timer > 0
    assert organism.wins == 1


@pytest.mark.usefixtures("fake_model")
def test_evaluate_new_tickers(organism):
    fitness = organism.evaluate_fitness(("GAZP", "LKOH"), pd.Timestamp("2020-04-12"))

    assert fitness == 5
    assert FakeModel.COUNTER == 2
    assert organism.wins == 2


@pytest.mark.usefixtures("fake_model")
def test_evaluate_new_timestamp(organism):
    fitness = organism.evaluate_fitness(("GAZP", "LKOH"), pd.Timestamp("2020-04-13"))

    assert fitness == 5
    assert FakeModel.COUNTER == 3
    assert organism.wins == 3


# noinspection PyProtectedMember
@pytest.fixture()
def make_weak_organism():
    weak = population.Organism()
    weak._doc.llh = -100
    weak._doc.timer = 100
    weak._doc.date = pd.Timestamp("2020-04-13")
    weak._doc.tickers = ("GAZP", "LKOH")

    yield weak

    weak.die()


def test_find_weaker(organism):
    found = organism.find_weaker()

    assert isinstance(found, population.Organism)
    assert found._doc.llh <= organism._doc.llh
    assert found._doc.timer >= organism._doc.timer


def test_die(organism):
    id_ = organism.id
    organism.die()

    with pytest.raises(store.IdError) as error:
        population.Organism(_id=id_)
    assert str(id_) == str(error.value)


# noinspection PyProtectedMember
@pytest.fixture(name="one_of_three")
def make_three_and_yield_one_organism():
    """Нужно минимум три организма для дифференциальной эволюции."""
    population.Organism().save()
    population.Organism().save()
    organism = population.Organism()
    organism.save()
    yield organism


def test_make_child(one_of_three):
    assert isinstance(one_of_three.make_child(1), population.Organism)


def test_raise_forecast_error():
    with pytest.raises(population.ForecastError) as error:
        population.Organism().forecast(("GAZP", "AKRN"), pd.Timestamp("2020-04-13"))
    assert isinstance(population.ForecastError(), error.type)


def test_forecast():
    org = population.Organism()
    org.evaluate_fitness(("GAZP", "AKRN"), pd.Timestamp("2020-04-21"))
    rez = org.forecast(("GAZP", "AKRN"), pd.Timestamp("2020-04-21"))

    assert isinstance(rez, Forecast)
    assert rez.date == pd.Timestamp("2020-04-21")
    assert rez.tickers == ("GAZP", "AKRN")


def test_count():
    assert population.count() == 4

    org1 = population.Organism()
    org1._doc.save()
    assert population.count() == 5

    org2 = population.Organism()
    org2._doc.save()
    assert population.count() == 6

    org1.die()
    assert population.count() == 5

    org2.die()
    assert population.count() == 4


def test_create_new_organism():
    org = population.create_new_organism()
    assert isinstance(org, population.Organism)

    assert population.Organism(_id=org.id).id == org.id
    org.die()


def test_get_all_and_random_organisms():
    organisms = population.get_all_organisms()
    assert isinstance(organisms, Iterable)

    organisms = list(organisms)

    for organism in organisms:
        assert isinstance(organism, population.Organism)

    assert len(list(organisms)) == 4

    ids = [organism.id for organism in organisms]

    org = population.get_random_organism()
    assert org.id in ids


def test_print_stat(capsys):
    population.print_stat()
    captured = capsys.readouterr()

    assert "Excess return" in captured.out
    assert "Максимум побед" in captured.out
