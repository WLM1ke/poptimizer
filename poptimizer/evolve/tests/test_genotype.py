from poptimizer.evolve import chromosomes
from poptimizer.evolve.chromosomes import chromosome
from poptimizer.evolve.genotype import Genotype


def test_get_phenotype():
    genotype_data = {"Data": {"batch_size": 3, "history_days": 4, "forecast_days": 5}}
    chromosomes_types = [chromosomes.Data]
    base_phenotype = {"type": "TestNet", "data": {"features": {"Prices": {}}}}
    genotype = Genotype(genotype_data, base_phenotype, chromosomes_types)
    result = {
        "type": "TestNet",
        "data": {
            "batch_size": 3,
            "history_days": 4,
            "forecast_days": 5,
            "features": {"Prices": {}, "Ticker": {"on": True}},
        },
    }
    assert result == genotype.get_phenotype()


def test_make_child(monkeypatch):
    chromosomes_types = [chromosomes.Data]

    parent = {"Data": {"batch_size": 3, "history_days": 4, "forecast_days": 5, "ticker_on": 2}}
    base = {"Data": {"batch_size": 2, "history_days": 5, "forecast_days": 4, "ticker_on": 3}}
    diff1 = {"Data": {"batch_size": 1, "history_days": 3, "forecast_days": 6, "ticker_on": 3}}
    diff2 = {"Data": {"batch_size": 4, "history_days": 6, "forecast_days": 3, "ticker_on": 1}}

    parent = Genotype(parent, all_chromosome_types=chromosomes_types)
    base = Genotype(base, all_chromosome_types=chromosomes_types)
    diff1 = Genotype(diff1, all_chromosome_types=chromosomes_types)
    diff2 = Genotype(diff2, all_chromosome_types=chromosomes_types)

    monkeypatch.setattr(chromosome.random, "rand", lambda _: (0.89, 0.91, 0.89, 0.89))

    child = parent.make_child(base, diff1, diff2)

    assert isinstance(child, Genotype)
    assert child.data == {
        "Data": {
            "batch_size": (2 + 1) / 2,
            "history_days": 4,
            "forecast_days": 4 + (6 - 3) * 0.8,
            "ticker_on": 3 + (3 - 1) * 0.8,
        }
    }
