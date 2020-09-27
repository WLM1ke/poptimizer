import pytest

from poptimizer.evolve import chromosomes, genotype
from poptimizer.evolve.chromosomes import chromosome, data
from poptimizer.evolve.genotype import Genotype

FAKE_GENES = (
    data.BATCH_SIZE,
    data.HISTORY_DAYS,
    data.TICKER_ON,
    data.DAY_OF_YEAR_ON,
    data.PRICES_ON,
    data.DIVIDENDS_ON,
    data.TURNOVER_ON,
    data.AVERAGE_TURNOVER_ON,
)


@pytest.fixture(scope="function", autouse=True)
def patch_features(monkeypatch):
    monkeypatch.setattr(genotype.ALL_CHROMOSOMES_TYPES[0], "_GENES", FAKE_GENES)


def test_get_phenotype():
    genotype_data = {"Data": {"batch_size": 3, "history_days": 4}}
    chromosomes_types = [chromosomes.Data]
    base_phenotype = {"type": "TestNet", "data": {"features": {"Prices": {}}}}
    genotype = Genotype(genotype_data, base_phenotype, chromosomes_types)
    result = {
        "type": "TestNet",
        "data": {
            "batch_size": 3,
            "history_days": 4,
            "features": {
                "Prices": {"on": True},
                "Dividends": {"on": True},
                "Turnover": {"on": True},
                "AverageTurnover": {"on": True},
                "Ticker": {"on": True},
                "DayOfYear": {"on": True},
            },
        },
    }
    assert result == genotype.get_phenotype()


def test_make_child(monkeypatch):
    chromosomes_types = [chromosomes.Data]

    parent = {
        "Data": {
            "batch_size": 3,
            "history_days": 4,
            "ticker_on": 2,
            "day_of_year_on": 1,
            "prices_on": 0,
            "dividends_on": 3,
            "turnover_on": 1,
            "average_turnover_on": 1,
        }
    }
    base = {
        "Data": {
            "batch_size": 2,
            "history_days": 5,
            "ticker_on": 3,
            "day_of_year_on": 7,
            "prices_on": 8,
            "dividends_on": 4,
            "turnover_on": 6,
            "average_turnover_on": 4,
        }
    }
    diff1 = {
        "Data": {
            "batch_size": 1,
            "history_days": 3,
            "ticker_on": 3,
            "day_of_year_on": 3,
            "prices_on": 3,
            "dividends_on": 1,
            "turnover_on": 4,
            "average_turnover_on": 2,
        }
    }
    diff2 = {
        "Data": {
            "batch_size": 4,
            "history_days": 6,
            "ticker_on": 1,
            "day_of_year_on": 8,
            "prices_on": 9,
            "dividends_on": 1,
            "turnover_on": 2,
            "average_turnover_on": 9,
        }
    }

    parent = Genotype(parent, all_chromosome_types=chromosomes_types)
    base = Genotype(base, all_chromosome_types=chromosomes_types)
    diff1 = Genotype(diff1, all_chromosome_types=chromosomes_types)
    diff2 = Genotype(diff2, all_chromosome_types=chromosomes_types)

    monkeypatch.setattr(
        chromosome.random, "rand", lambda _: (0.89, 0.91, 0.89, 0.89, 0.89, 0.91, 0.89, 0.91)
    )

    child = parent.make_child(base, diff1, diff2)

    assert isinstance(child, Genotype)
    assert child.data == {
        "Data": {
            "batch_size": (2 + 1) / 2,
            "history_days": 4,
            "ticker_on": 3 + (3 - 1) * 0.8,
            "day_of_year_on": 7 + (3 - 8) * 0.8,
            "prices_on": 8 + (3 - 9) * 0.8,
            "dividends_on": 3,
            "turnover_on": 6 + (4 - 2) * 0.8,
            "average_turnover_on": 1,
        }
    }
