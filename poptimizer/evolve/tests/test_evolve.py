import pandas as pd

from poptimizer.dl import ModelError
from poptimizer.evolve import evolve
from poptimizer.portfolio import Portfolio


class FakeOrganism:
    def __init__(self, fitness, timer, child_fitness, child_timer, population):
        self._fitness = fitness
        self._timer = timer
        self._child_fitness = child_fitness
        self._child_timer = child_timer
        self._population = population
        self._population.add(self)

    @property
    def wins(self):
        return

    @property
    def timer(self):
        return self._timer * 10 ** 9

    # noinspection PyUnusedLocal
    def evaluate_fitness(self, tickers, end):
        if self._fitness is None:
            raise ModelError
        return self._fitness

    # noinspection PyProtectedMember
    def find_weaker(self):
        population = filter(lambda x: x._fitness <= self._fitness, self._population._organisms.values())
        return max(population, key=lambda x: x._timer)

    def die(self):
        self._population.kill(self)

    def make_child(self, _):
        return FakeOrganism(self._child_fitness, self._child_timer, None, None, self._population)

    @property
    def id(self):
        return object()


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
    params = (None, None, None, None)
    organisms_params = [params, params]
    new_organisms_params = [params, params, params, params]
    fake_population = FakePopulation(organisms_params, new_organisms_params)
    monkeypatch.setattr(evolve, "population", fake_population)
    ev = evolve.Evolution(5)
    assert fake_population.count() == 2
    ev._setup()
    assert fake_population.count() == 5


def test_setup_not_needed(monkeypatch):
    params = (None, None, None, None)
    organisms_params = [
        params,
        params,
        params,
        params,
        params,
    ]
    new_organisms_params = []
    fake_population = FakePopulation(organisms_params, new_organisms_params)
    monkeypatch.setattr(evolve, "population", fake_population)
    ev = evolve.Evolution(5)
    assert fake_population.count() == 5
    ev._setup()
    assert fake_population.count() == 5


# noinspection DuplicatedCode
def test_evolve_parent(monkeypatch):
    organisms_params = [(4, 1, 3, 2), (4, 1, 3, 2), (5, 1, 4, 2), (4, 1, 3, 2)]
    new_organisms_params = []
    fake_population = FakePopulation(organisms_params, new_organisms_params)
    monkeypatch.setattr(evolve, "population", fake_population)
    population_ids = list(fake_population._organisms)
    ev = evolve.Evolution(4)
    assert fake_population.count() == 4
    port = Portfolio(pd.Timestamp("2020-04-19"), 0, dict(AKRN=0))
    ev.evolve(port)
    assert fake_population.count() == 4
    assert list(fake_population._organisms) == population_ids


class BadFakeOrganism:
    wins = 3
    dead = False

    def evaluate_fitness(self, tickers, end):
        raise ModelError

    def die(self):
        self.dead = True


def test_evolve_bad_parent(monkeypatch, capsys):
    org = BadFakeOrganism()
    # noinspection PyTypeChecker
    assert evolve.Evolution(4)._eval_and_print(org, None, None) is None
    assert org.dead is True
    captured = capsys.readouterr()
    assert "Удаляю - ModelError" in captured.out
