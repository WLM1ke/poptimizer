import pandas as pd

from poptimizer.dl import ModelError
from poptimizer.evolve import evolve


class FakeOrganism:
    def __init__(self, fitness, child_fitness, population):
        self._fitness = fitness
        self._child_fitness = child_fitness
        self._population = population
        self._population.add(self)

    @property
    def wins(self):
        return

    # noinspection PyUnusedLocal
    def evaluate_fitness(self, tickers, end):
        if self._fitness is None:
            raise ModelError
        return self._fitness

    def die(self):
        self._population.kill(self)

    def make_child(self):
        return FakeOrganism(self._child_fitness, None, self._population)


class FakePopulation:
    def __init__(self, organisms_params, new_organisms_params):
        self.new_organisms_params = new_organisms_params
        self._organisms = {}
        for params in organisms_params:
            organism = FakeOrganism(*params, self)
            self._organisms[id(organism)] = organism

    def kill(self, organism):
        self._organisms.pop(id(organism))

    def add(self, organism):
        self._organisms[id(organism)] = organism

    def count(self):
        return len(self._organisms)

    def get_all_organisms(self):
        yield from list(self._organisms.values())

    def print_stat(self):
        pass

    def create_new_organism(self):
        params = self.new_organisms_params.pop()
        return FakeOrganism(*params, self)


def test_setup_needed(monkeypatch):
    organisms_params = [(None, None), (None, None)]
    new_organisms_params = [(None, None), (None, None), (None, None), (None, None)]
    fake_population = FakePopulation(organisms_params, new_organisms_params)
    monkeypatch.setattr(evolve, "population", fake_population)
    ev = evolve.Evolution(5)
    assert fake_population.count() == 2
    ev._setup()
    assert fake_population.count() == 5


def test_setup_not_needed(monkeypatch):
    organisms_params = [
        (None, None),
        (None, None),
        (None, None),
        (None, None),
        (None, None),
    ]
    new_organisms_params = []
    fake_population = FakePopulation(organisms_params, new_organisms_params)
    monkeypatch.setattr(evolve, "population", fake_population)
    ev = evolve.Evolution(5)
    assert fake_population.count() == 5
    ev._setup()
    assert fake_population.count() == 5


# noinspection DuplicatedCode
def test_evolve_parent_win(monkeypatch):
    organisms_params = [(4, 3), (4, 3), (5, 4), (4, 3)]
    new_organisms_params = []
    fake_population = FakePopulation(organisms_params, new_organisms_params)
    monkeypatch.setattr(evolve, "population", fake_population)
    population_ids = list(fake_population._organisms)
    ev = evolve.Evolution(4)
    assert fake_population.count() == 4
    ev.evolve(("AKRN",), pd.Timestamp("2020-04-19"))
    assert fake_population.count() == 4
    assert list(fake_population._organisms) == population_ids


# noinspection DuplicatedCode
def test_evolve_parent_loose(monkeypatch):
    organisms_params = [(4, 3), (4, 3), (5, 4), (3, 4)]
    new_organisms_params = []
    fake_population = FakePopulation(organisms_params, new_organisms_params)
    monkeypatch.setattr(evolve, "population", fake_population)
    population_ids = list(fake_population._organisms)
    ev = evolve.Evolution(4)
    assert fake_population.count() == 4
    ev.evolve(("AKRN",), pd.Timestamp("2020-04-19"))
    assert fake_population.count() == 4
    assert list(fake_population._organisms)[:-1] == population_ids[:-1]
    assert list(fake_population._organisms)[-1] != population_ids[-1]


# noinspection DuplicatedCode
def test_evolve_parent_loose_no_excess(monkeypatch):
    organisms_params = [(4, 3), (4, 3), (None, 4), (3, 4)]
    new_organisms_params = []
    fake_population = FakePopulation(organisms_params, new_organisms_params)
    monkeypatch.setattr(evolve, "population", fake_population)
    population_ids = list(fake_population._organisms)
    ev = evolve.Evolution(4)
    assert fake_population.count() == 4
    ev.evolve(("AKRN",), pd.Timestamp("2020-04-19"))
    assert fake_population.count() == 4
    assert list(fake_population._organisms)[:2] == population_ids[:2]
    assert list(fake_population._organisms)[2] == population_ids[3]
    assert list(fake_population._organisms)[3] not in population_ids


def test_evolve_bad_parent(monkeypatch, capsys):
    organisms_params = [(4, 3), (4, 3), (5, 4), (None, None)]
    new_organisms_params = []
    fake_population = FakePopulation(organisms_params, new_organisms_params)
    monkeypatch.setattr(evolve, "population", fake_population)
    population_ids = list(fake_population._organisms)[:-1]
    ev = evolve.Evolution(4)
    assert fake_population.count() == 4
    ev.evolve(("AKRN",), pd.Timestamp("2020-04-19"))
    assert fake_population.count() == 3
    assert list(fake_population._organisms) == population_ids
    captured = capsys.readouterr()
    assert "Удаляю родителя - ModelError" in captured.out


# noinspection DuplicatedCode
def test_evolve_bad_child(monkeypatch, capsys):
    organisms_params = [(4, 3), (4, 3), (5, 4), (1, None)]
    new_organisms_params = []
    fake_population = FakePopulation(organisms_params, new_organisms_params)
    monkeypatch.setattr(evolve, "population", fake_population)
    population_ids = list(fake_population._organisms)
    ev = evolve.Evolution(4)
    assert fake_population.count() == 4
    ev.evolve(("AKRN",), pd.Timestamp("2020-04-19"))
    assert fake_population.count() == 4
    assert list(fake_population._organisms) == population_ids
    captured = capsys.readouterr()
    assert "Удаляю потомка - ModelError" in captured.out
